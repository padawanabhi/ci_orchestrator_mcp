# Placeholder for authentication utilities (token loading, etc) 

import os
import httpx
from src.mcp.error import JsonRpcError, INTERNAL_ERROR

# No internal imports yet, but use src. prefix if needed in the future.

def get_github_credentials():
    token = os.environ.get("GITHUB_TOKEN")
    owner = os.environ.get("GITHUB_OWNER")
    repo = os.environ.get("GITHUB_REPO")

    if not token or not owner or not repo:
        raise RuntimeError("Missing GITHUB_TOKEN, GITHUB_OWNER, or GITHUB_REPO in environment")
    return token, owner, repo 

""" async def verify_github_access():
    token, owner, repo = get_github_credentials()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{owner}/{repo}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise JsonRpcError(INTERNAL_ERROR, f"GitHub repo access failed: {resp.status_code}", resp.text)  """

async def verify_github_access():
    token, owner, repo = get_github_credentials()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    endpoints = [
        ("repo", base_url),
        ("workflows", f"{base_url}/actions/workflows"),
        ("runs", f"{base_url}/actions/runs"),
        ("runners", f"{base_url}/actions/runners"),
    ]
    async with httpx.AsyncClient() as client:
        for name, url in endpoints:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 403:
                raise JsonRpcError(
                    INTERNAL_ERROR,
                    f"GitHub {name} endpoint forbidden (403). Check token permissions for {url}.",
                    resp.text,
                )
            elif resp.status_code == 404:
                raise JsonRpcError(
                    INTERNAL_ERROR,
                    f"GitHub {name} endpoint not found (404). Check repo name/visibility for {url}.",
                    resp.text,
                )
            elif resp.status_code != 200:
                raise JsonRpcError(
                    INTERNAL_ERROR,
                    f"GitHub {name} endpoint error: {resp.status_code} for {url}.",
                    resp.text,
                )