const API_URL = 'http://localhost:8080/jsonrpc';
const STREAM_BASE = 'http://localhost:8080/stream/logs?run_id=';

function setStatus(msg, isError = false) {
  const status = document.getElementById('status');
  status.textContent = msg;
  status.style.color = isError ? 'red' : 'green';
}

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
  data.result.forEach(r => {
    const li = document.createElement('li');
    li.textContent = `${r.type}: ${r.name} (id: ${r.id})`;
    list.appendChild(li);
  });
}

document.getElementById('refresh-resources').onclick = listResources;
window.onload = listResources;

document.getElementById('trigger-form').onsubmit = async (e) => {
  e.preventDefault();
  const workflowId = document.getElementById('workflow-id').value;
  const ref = document.getElementById('workflow-ref').value;
  setStatus('Triggering workflow...');
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'github/execute',
      params: {
        action: 'trigger_workflow',
        workflow_id: workflowId,
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
  const runId = document.getElementById('run-id').value;
  const output = document.getElementById('logs-output');
  output.textContent = '';
  setStatus('Streaming logs...');
  const es = new EventSource(STREAM_BASE + encodeURIComponent(runId));
  es.onmessage = (event) => {
    // Parse [filename] log lines
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
  es.onerror = (e) => {
    setStatus('Log stream ended or error.', true);
    es.close();
  };
}; 