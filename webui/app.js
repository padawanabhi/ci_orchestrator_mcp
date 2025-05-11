const API_URL = 'http://localhost:8080/jsonrpc';
const STREAM_BASE = 'http://localhost:8080/stream/logs?run_id=';

function setStatus(msg, isError = false) {
  const status = document.getElementById('status');
  status.textContent = msg;
  status.style.color = isError ? 'red' : 'green';
}

let workflows = [];
let runs = [];

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
  setStatus('Workflow triggered.');
  resultDiv.textContent = JSON.stringify(data.result, null, 2);
};

document.getElementById('logs-form').onsubmit = (e) => {
  e.preventDefault();
  let runId = document.getElementById('run-id').value.trim();
  if (!/^[0-9]+$/.test(runId)) {
    setStatus('Run ID must be numeric.', true);
    return;
  }
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
      output.textContent += `[${filename}] ${line}\n`;
    } else {
      output.textContent += event.data + '\n';
    }
    output.scrollTop = output.scrollHeight;
  };
  es.onerror = async (e) => {
    es.close();
    if (!gotData) {
      setStatus('No logs streamed. Attempting to fetch finished logs...');
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
        output.textContent = data.result.logs;
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
}; 