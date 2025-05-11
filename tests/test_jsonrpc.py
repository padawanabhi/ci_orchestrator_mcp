import pytest
from httpx import AsyncClient
import asyncio
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8080"

@pytest.mark.asyncio
async def test_github_resources_list():
    await asyncio.sleep(0.1)  # Give server a moment to start if needed
    async with AsyncClient(base_url=BASE_URL) as ac:
        resp = await ac.post("/jsonrpc", json={
            "jsonrpc": "2.0",
            "method": "github/resources/list",
            "params": {},
            "id": 1
        })
        print("RESPONSE BODY:", resp.text)  
        assert resp.status_code == 200
        data = resp.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert isinstance(data["result"], list)
        if data["result"]:
            assert any(r["type"] in ("workflow", "workflow_run", "runner") for r in data["result"])
        else:
            print("No workflows, runs, or runners found in the repo (this is valid for an empty repo).")
        # # At least one of the types should be present if repo has workflows/runs/runners
        # assert any(r["type"] in ("workflow", "workflow_run", "runner") for r in data["result"])

@pytest.mark.asyncio
async def test_invalid_jsonrpc_schema():
    async with AsyncClient(base_url=BASE_URL) as ac:
        resp = await ac.post("/jsonrpc", json={"foo": "bar"})
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # INVALID_REQUEST

@pytest.mark.asyncio
async def test_method_not_found():
    async with AsyncClient(base_url=BASE_URL) as ac:
        resp = await ac.post("/jsonrpc", json={
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "id": 2
        })
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND
        assert data["id"] == 2 