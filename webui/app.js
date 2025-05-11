const API_URL = 'http://localhost:8080/jsonrpc';
const STREAM_BASE = 'http://localhost:8080/stream/logs?run_id=';

function setStatus(msg, isError = false) {
  const status = document.getElementById('status');
  status.textContent = msg;
  status.style.color = isError ? 'red' : 'green';
}

let workflows = [];
let runs = [];
let lastLogs = [];
let lastRawLogs = '';
let lastRunId = null;

async function listResources() {
  setStatus('Loading resources...');
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'github/resources/list',
      params: {},
      id: 1
    })
  });
  const data = await res.json();
  if (data.error) {
    setStatus('Error: ' + data.error.message, true);
    return;
  }
  setStatus('Resources loaded.');
  const list = document.getElementById('resources-list');
  list.innerHTML = '';
  workflows = data.result.filter(r => r.type === 'workflow');
  runs = data.result.filter(r => r.type === 'workflow_run');
  data.result.forEach(r => {
    const li = document.createElement('li');
    if (r.type === 'workflow') {
      li.textContent = `${r.type}: ${r.name} (id: ${r.id.replace('wf_', '')})`;
    } else if (r.type === 'workflow_run') {
      li.textContent = `${r.type}: ${r.name} (id: ${r.id.replace('run_', '')})`;
    } else {
      li.textContent = `${r.type}: ${r.name} (id: ${r.id})`;
    }
    list.appendChild(li);
  });
}

document.getElementById('refresh-resources').onclick = listResources;
window.onload = listResources;

async function pollForNewRun(workflowId, ref, callback) {
  let attempts = 0;
  while (attempts < 20) { // poll up to 20 times (about 20s)
    await new Promise(r => setTimeout(r, 1000));
    await listResources();
    const found = runs.find(r => r.name === ref || r.name === undefined || r.workflow_id === workflowId);
    if (found) {
      callback(found.id.replace('run_', ''));
      return;
    }
    attempts++;
  }
  setStatus('Could not find new run after triggering workflow.', true);
}

document.getElementById('trigger-form').onsubmit = async (e) => {
  e.preventDefault();
  let workflowId = document.getElementById('workflow-id').value.trim();
  const ref = document.getElementById('workflow-ref').value.trim();
  if (!/^[0-9]+$/.test(workflowId)) {
    setStatus('Workflow ID must be numeric.', true);
    return;
  }
  setStatus('Triggering workflow...');
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'github/execute',
      params: {
        action: 'trigger_workflow',
        workflow_id: parseInt(workflowId, 10),
        ref: ref
      },
      id: 2
    })
  });
  const data = await res.json();
  const resultDiv = document.getElementById('trigger-result');
  if (data.error) {
    setStatus('Error: ' + data.error.message, true);
    resultDiv.textContent = '';
    return;
  }
  setStatus('Workflow triggered. Polling for new run...');
  resultDiv.textContent = JSON.stringify(data.result, null, 2);
  // Poll for the new run and auto-stream logs
  pollForNewRun(workflowId, ref, (runId) => {
    document.getElementById('run-id').value = runId;
    streamLogs(runId);
  });
};

function renderLogs() {
  const output = document.getElementById('logs-output');
  const search = document.getElementById('log-search').value.toLowerCase();
  const filter = document.getElementById('log-filter').value;
  let filtered = lastLogs;
  if (filter) {
    filtered = filtered.filter(l => l.filename === filter);
  }
  if (search) {
    filtered = filtered.filter(l => l.line.toLowerCase().includes(search));
  }
  output.textContent = filtered.map(l => `[${l.filename}] ${l.line}`).join('\n');
}

document.getElementById('log-search').oninput = renderLogs;
document.getElementById('log-filter').onchange = renderLogs;
document.getElementById('log-download').onclick = () => {
  const blob = new Blob([document.getElementById('logs-output').textContent], {type: 'text/plain'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `logs_run_${lastRunId || 'unknown'}.txt`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 100);
};

function updateLogFilterOptions() {
  const select = document.getElementById('log-filter');
  const filenames = Array.from(new Set(lastLogs.map(l => l.filename)));
  select.innerHTML = '<option value="">All Jobs/Steps</option>' + filenames.map(f => `<option value="${f}">${f}</option>`).join('');
}

function streamLogs(runId) {
  lastRunId = runId;
  lastLogs = [];
  lastRawLogs = '';
  const output = document.getElementById('logs-output');
  output.textContent = '';
  setStatus('Streaming logs...');
  const es = new EventSource(STREAM_BASE + encodeURIComponent(runId));
  let gotData = false;
  es.onmessage = (event) => {
    gotData = true;
    const match = event.data.match(/^\[(.+?)\] (.*)$/);
    if (match) {
      const filename = match[1];
      const line = match[2];
      lastLogs.push({filename, line});
    } else {
      lastLogs.push({filename: '', line: event.data});
    }
    renderLogs();
    updateLogFilterOptions();
    output.scrollTop = output.scrollHeight;
  };
  es.onerror = async (e) => {
    es.close();
    if (!gotData) {
      setStatus('No logs streamed. Attempting to fetch finished logs...');
      console.log('Fallback: fetching finished logs for run_id', runId);
      // Fallback: fetch finished logs via JSON-RPC
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'github/execute',
          params: {
            action: 'fetch_logs',
            run_id: parseInt(runId, 10)
          },
          id: 4
        })
      });
      const data = await res.json();
      if (data.result && data.result.logs) {
        lastRawLogs = data.result.logs;
        // Parse logs into lines for search/filter
        lastLogs = data.result.logs.split('\n').map(line => {
          const m = line.match(/^\[(.+?)\] (.*)$/);
          if (m) return {filename: m[1], line: m[2]};
          return {filename: '', line};
        });
        renderLogs();
        updateLogFilterOptions();
        setStatus('Fetched finished logs.');
      } else if (data.error) {
        setStatus('Error fetching finished logs: ' + data.error.message, true);
      } else {
        setStatus('No logs available for this run.', true);
      }
    } else {
      setStatus('Log stream ended or error.', true);
    }
  };
}

document.getElementById('logs-form').onsubmit = (e) => {
  e.preventDefault();
  let runId = document.getElementById('run-id').value.trim();
  if (!/^[0-9]+$/.test(runId)) {
    setStatus('Run ID must be numeric.', true);
    return;
  }
  streamLogs(runId);
}; 