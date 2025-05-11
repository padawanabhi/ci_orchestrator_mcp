# Placeholder for GitHub execute logic 
from typing import Any, Dict
from src.utils.auth import get_github_credentials
from src.mcp.error import JsonRpcError, INVALID_PARAMS, INTERNAL_ERROR
import httpx
import asyncio
import zipfile
import io

GITHUB_API = "https://api.github.com"

async def github_execute(params: Dict[str, Any]) -> Any:
    token, owner, repo = get_github_credentials()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    action = params.get("action")
    if not action:
        raise JsonRpcError(INVALID_PARAMS, "Missing 'action' in params")
    async with httpx.AsyncClient() as client:
        try:
            if action == "trigger_workflow":
                workflow_id = params.get("workflow_id")
                ref = params.get("ref")
                inputs = params.get("inputs", {})
                if not workflow_id or not ref:
                    raise JsonRpcError(INVALID_PARAMS, "'workflow_id' and 'ref' are required for trigger_workflow")
                url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
                resp = await client.post(url, headers=headers, json={"ref": ref, "inputs": inputs})
                if resp.status_code != 204:
                    raise JsonRpcError(INTERNAL_ERROR, f"Failed to trigger workflow: {resp.status_code}", resp.text)
                return {"status": "workflow triggered", "workflow_id": workflow_id, "ref": ref}
            elif action == "cancel_run":
                run_id = params.get("run_id")
                if not run_id:
                    raise JsonRpcError(INVALID_PARAMS, "'run_id' is required for cancel_run")
                url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/cancel"
                resp = await client.post(url, headers=headers)
                if resp.status_code != 202:
                    raise JsonRpcError(INTERNAL_ERROR, f"Failed to cancel run: {resp.status_code}", resp.text)
                return {"status": "run cancelled", "run_id": run_id}
            elif action == "rerun_run":
                run_id = params.get("run_id")
                if not run_id:
                    raise JsonRpcError(INVALID_PARAMS, "'run_id' is required for rerun_run")
                url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"
                resp = await client.post(url, headers=headers)
                if resp.status_code != 201:
                    raise JsonRpcError(INTERNAL_ERROR, f"Failed to rerun run: {resp.status_code}", resp.text)
                return {"status": "run rerun triggered", "run_id": run_id}
            elif action == "fetch_logs":
                run_id = params.get("run_id")
                if not run_id:
                    raise JsonRpcError(INVALID_PARAMS, "'run_id' is required for fetch_logs")
                url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
                resp = await client.get(url, headers=headers, follow_redirects=True)
                if resp.status_code != 200:
                    print(f"[fetch_logs] Failed to fetch logs: {resp.status_code} {resp.text}")
                    if resp.status_code == 302:
                        print(f"[fetch_logs] Redirected to: {resp.headers.get('location')}")
                    raise JsonRpcError(INTERNAL_ERROR, f"Failed to fetch logs: {resp.status_code}", resp.text)
                # Unzip and concatenate all log lines as plaintext
                try:
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                        all_lines = []
                        for filename in z.namelist():
                            with z.open(filename) as f:
                                for line in f:
                                    all_lines.append(f"[{filename}] {line.decode(errors='replace').rstrip()}")
                        print(f"[fetch_logs] {len(all_lines)} log lines fetched for run_id={run_id}")
                        print("[fetch_logs] Sample log lines:")
                        for l in all_lines[:10]:
                            print(l)
                        return {"status": "logs fetched", "run_id": run_id, "logs": "\n".join(all_lines)}
                except zipfile.BadZipFile:
                    text = resp.content.decode(errors="replace")
                    print(f"[fetch_logs] Non-zip log content for run_id={run_id} (length={len(text)})")
                    print(text[:500])
                    return {"status": "logs fetched", "run_id": run_id, "logs": text}
            else:
                raise JsonRpcError(INVALID_PARAMS, f"Unknown action: {action}")
        except JsonRpcError:
            raise
        except Exception as e:
            print(f"[fetch_logs] Exception: {e}")
            raise JsonRpcError(INTERNAL_ERROR, f"GitHub execute error: {str(e)}") 