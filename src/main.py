"""
FastAPI MCP server entrypoint. Also serves the web UI at /ui/.
"""
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from src.mcp.schema import validate_jsonrpc_request
from src.mcp.error import JsonRpcError, INTERNAL_ERROR, METHOD_NOT_FOUND
from src.github.resources import github_resources_list
from src.github.execute import github_execute
from src.jenkins.resources import jenkins_resources_list
from src.jenkins.execute import jenkins_execute
from src.utils.auth import verify_github_access, get_github_credentials
from src.utils.streaming import stream_github_logs
import inspect
import sys
import os

app = FastAPI()

# Serve the web UI at /ui/
webui_path = os.path.join(os.path.dirname(__file__), '..', 'webui')
app.mount("/ui", StaticFiles(directory=webui_path, html=True), name="ui")

@app.on_event("startup")
async def check_github_connectivity():
    try:
        await verify_github_access()
        print("[Startup] GitHub connectivity check passed.")
    except Exception as e:
        print(f"[Startup] GitHub connectivity check failed: {e}")
        sys.exit(1)

# Dispatcher mapping method names to handler functions
dispatcher = {
    "github/resources/list": github_resources_list,
    "github/execute": github_execute,
    "jenkins/resources/list": jenkins_resources_list,
    "jenkins/execute": jenkins_execute,
}

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.get("/stream/logs")
async def stream_logs(run_id: int = Query(..., description="Numeric workflow run ID")):
    if not isinstance(run_id, int) or run_id <= 0:
        return JSONResponse(status_code=422, content={"error": "run_id must be a positive integer"})
    token, owner, repo = get_github_credentials()
    generator = stream_github_logs(owner, repo, run_id, token)
    return StreamingResponse(generator, media_type="text/event-stream")

@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: Request):
    try:
        body = await request.json()
        validate_jsonrpc_request(body)
        method = body["method"]
        params = body.get("params", {})
        handler = dispatcher.get(method)
        if not handler:
            raise JsonRpcError(METHOD_NOT_FOUND, f"Method '{method}' not found")
        if inspect.iscoroutinefunction(handler):
            # Special case: for github/execute fetch_logs, return stream URL
            if method == "github/execute" and params.get("action") == "fetch_logs":
                run_id = params.get("run_id")
                if not isinstance(run_id, int) or run_id <= 0:
                    raise JsonRpcError(INTERNAL_ERROR, "'run_id' must be a positive integer for fetch_logs streaming")
                # Return the stream URL for the client to connect to
                url = f"/stream/logs?run_id={run_id}"
                return JSONResponse(content={"jsonrpc": "2.0", "result": {"stream_url": url, "run_id": run_id}, "id": body.get("id")})
            result = await handler(params)
        else:
            result = handler(params)
        return JSONResponse(content={"jsonrpc": "2.0", "result": result, "id": body.get("id")})
    except JsonRpcError as e:
        return JSONResponse(content=e.to_response(getattr(body, 'get', lambda _: None)("id")), status_code=400)
    except Exception as e:
        err = JsonRpcError(INTERNAL_ERROR, "Internal error", str(e))
        return JSONResponse(content=err.to_response(getattr(body, 'get', lambda _: None)("id")), status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080) 