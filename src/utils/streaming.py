# Placeholder for streaming utilities (SSE, chunked log streaming, etc) 

import httpx
import asyncio
from typing import AsyncGenerator
import zipfile
import io

async def stream_github_logs(owner: str, repo: str, run_id: int, token: str) -> AsyncGenerator[str, None]:
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        if resp.status_code != 200:
            if resp.status_code == 302:
                yield f"event: error\ndata: Redirected to: {resp.headers.get('location')}\n\n"
            yield f"event: error\ndata: Failed to fetch logs: {resp.status_code} {resp.text}\n\n"
            return
        # Unzip in memory
        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                for filename in z.namelist():
                    with z.open(filename) as f:
                        for line in f:
                            await asyncio.sleep(0)  # Yield control to event loop
                            # Prefix with filename for context
                            yield f"data: [{filename}] {line.decode(errors='replace').rstrip()}\n\n"
        except zipfile.BadZipFile:
            # If not a zip, stream as plain text
            for line in resp.iter_bytes():
                await asyncio.sleep(0)
                yield f"data: {line.decode(errors='replace').rstrip()}\n\n" 