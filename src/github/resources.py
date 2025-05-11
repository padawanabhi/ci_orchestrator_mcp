# Placeholder for GitHub resources/list logic 
from typing import Any, Dict, List
from src.utils.auth import get_github_credentials
from src.mcp.error import JsonRpcError, INTERNAL_ERROR
import httpx
import asyncio

GITHUB_API = "https://api.github.com"

async def fetch_github(endpoint: str, token: str) -> Any:
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GITHUB_API}{endpoint}", headers=headers)
        if resp.status_code != 200:
            raise JsonRpcError(INTERNAL_ERROR, f"GitHub API error: {resp.status_code}", resp.text)
        return resp.json()

async def github_resources_list(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        token, owner, repo = get_github_credentials()
        # Fetch all three in parallel
        workflows_task = fetch_github(f"/repos/{owner}/{repo}/actions/workflows", token)
        runs_task = fetch_github(f"/repos/{owner}/{repo}/actions/runs", token)
        runners_task = fetch_github(f"/repos/{owner}/{repo}/actions/runners", token)
        workflows, runs, runners = await asyncio.gather(workflows_task, runs_task, runners_task)
        resources = []
        # Workflows
        for wf in workflows.get("workflows", []):
            resources.append({
                "id": f"wf_{wf['id']}",
                "type": "workflow",
                "name": wf.get("name") or wf.get("path") or wf.get("id")
            })
        # Workflow Runs
        for run in runs.get("workflow_runs", []):
            resources.append({
                "id": f"run_{run['id']}",
                "type": "workflow_run",
                "name": run.get("name") or run.get("head_branch") or run.get("id")
            })
        # Self-hosted Runners
        for runner in runners.get("runners", []):
            resources.append({
                "id": f"runner_{runner['id']}",
                "type": "runner",
                "name": runner.get("name") or runner.get("id")
            })
        return resources
    except JsonRpcError:
        raise
    except Exception as e:
        raise JsonRpcError(INTERNAL_ERROR, "Failed to list GitHub resources", str(e)) 