import asyncio
from src.utils.streaming import stream_github_logs
from src.utils.auth import get_github_credentials

async def test_stream():
    token, owner, repo = get_github_credentials()
    run_id = 14958730968  # Replace with your test run ID if needed
    async for line in stream_github_logs(owner, repo, run_id, token):
        print(line, end="")

if __name__ == "__main__":
    asyncio.run(test_stream()) 