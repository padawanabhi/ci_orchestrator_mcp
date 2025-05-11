# CI Orchestrator MCP Server

[![CI](https://github.com/padawanabhi/ci_orchestrator_mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/padawanabhi/ci_orchestrator_mcp/actions/workflows/ci.yml)

A Model Context Protocol (MCP) v1.0 server for orchestrating CI/CD workflows across GitHub Actions (including self-hosted runners) and Jenkins, using JSON-RPC 2.0 over HTTP.

## Features
- List and trigger GitHub Actions workflows, runners, and jobs
- List and trigger Jenkins jobs, stream logs
- JSON-RPC 2.0 API (MCP v1.0)
- Real-time log streaming via SSE/JSON-RPC notifications
- Secure token-based authentication
- **Web UI for demo and manual testing**

## Quickstart

### 1. Clone and Install
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your GitHub and Jenkins credentials.

**Required Environment Variables:**
- `GITHUB_TOKEN`: GitHub personal access token (classic or fine-grained)
- `GITHUB_OWNER`: GitHub org or username
- `GITHUB_REPO`: GitHub repository name

**Recommended GitHub Token Permissions:**
- `repo`, `workflow`, `admin:org`, `admin:repo_hook`
- For fine-grained tokens: "Actions: Read and Write", "Self-hosted runners: Read", and repo access

### 3. Run the Server
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

### 4. Web UI (Demo)
Open `webui/index.html` in your browser. The UI will connect to your running MCP server at `http://localhost:8080`.

**The UI lets you:**
- List GitHub workflows, runs, and runners
- Trigger a workflow
- Stream logs for a workflow run (with job/step context)
- See error messages and statuses

### 5. Docker
```bash
docker build -t ci-orchestrator .
docker run --env-file .env -p 8080:8080 ci-orchestrator
```

## API
- POST `/jsonrpc` — JSON-RPC 2.0 endpoint
- GET `/healthz` — Health check
- GET `/stream/logs?run_id=...` — Stream logs for a workflow run (SSE)

### `github/execute` Method

**Params:**
- `action`: One of `trigger_workflow`, `cancel_run`, `rerun_run`, `fetch_logs`
- Additional fields depending on action:
  - `trigger_workflow`: `workflow_id` (int), `ref` (str), `inputs` (dict, optional)
  - `cancel_run`/`rerun_run`/`fetch_logs`: `run_id` (int)

**Examples:**

Trigger a workflow:
```json
{
  "jsonrpc": "2.0",
  "method": "github/execute",
  "params": {
    "action": "trigger_workflow",
    "workflow_id": 123456,
    "ref": "main",
    "inputs": {"param1": "value"}
  },
  "id": 1
}
```

Cancel a workflow run:
```json
{
  "jsonrpc": "2.0",
  "method": "github/execute",
  "params": {
    "action": "cancel_run",
    "run_id": 789012
  },
  "id": 2
}
```

Fetch logs for a run:
```json
{
  "jsonrpc": "2.0",
  "method": "github/execute",
  "params": {
    "action": "fetch_logs",
    "run_id": 789012
  },
  "id": 3
}
```

## Cursor Integration

You can use this server directly with Cursor's MCP client by pointing to your local MCP server in `cursor.yaml`:
```yaml
mcpServers:
  - name: ci-orchestrator
    command: ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
    transport: http
    port: 8080
```

## Development
- Python 3.11+
- FastAPI, httpx, pytest

## License
MIT
