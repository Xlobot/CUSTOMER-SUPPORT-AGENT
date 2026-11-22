/**
 * static/monitoring.js — NetCare AI
 * Live polling of in-memory temporary logs and server telemetry.
 */

let autoRefreshInterval = null;
let isAutoRefreshActive = true;

async function fetchServerStatus() {
  try {
    const res = await fetch("/api/monitoring/status");
    if (!res.ok) throw new Error("Status fetch failed");
    const data = await res.json();

    document.getElementById("stat-uptime").textContent = data.uptime || "00h 00m 00s";

    if (data.model_status) {
      const ms = data.model_status;
      document.getElementById("stat-model-status").textContent = ms.loaded ? "Loaded & Operational" : "Not Loaded";
      document.getElementById("stat-model-status").style.color = ms.loaded ? "#10B981" : "#EF4444";
      document.getElementById("stat-model-name").textContent = `${ms.model_name} (Acc: ${(ms.val_accuracy * 100).toFixed(1)}%)`;
    }

    if (data.counters) {
      document.getElementById("stat-requests").textContent = `${data.counters.total_requests || 0} Total`;
      document.getElementById("stat-agent-calls").textContent = `${data.counters.agent_invocations || 0} Agent Invocations • ${data.counters.errors || 0} Errors`;
    }
  } catch (err) {
    console.warn("Could not fetch server status:", err);
  }
}

async function fetchLogs() {
  try {
    const level = document.getElementById("log-filter-level").value;
    const url = `/api/monitoring/logs?limit=150${level ? `&level=${level}` : ""}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Logs fetch failed");
    const logs = await res.json();

    renderLogs(logs);
    updateAgentCards(logs);
  } catch (err) {
    console.warn("Could not fetch temporary logs:", err);
  }
}

function renderLogs(logs) {
  const terminal = document.getElementById("log-terminal");
  if (!terminal) return;

  if (!logs || logs.length === 0) {
    terminal.innerHTML = "<div style='color:#64748B;'>No runtime logs currently buffered in memory.</div>";
    return;
  }

  let html = "";
  logs.forEach(l => {
    let levelColor = "#38BDF8";
    if (l.level === "WARN") levelColor = "#F59E0B";
    if (l.level === "ERROR") levelColor = "#EF4444";
    if (l.level === "SUCCESS") levelColor = "#10B981";

    const latencyText = l.latency_ms ? `<span style="color:#A855F7;margin-left:8px;">[${l.latency_ms}ms]</span>` : "";
    const resultText = l.result ? `<span style="color:#94A3B8;margin-left:8px;">→ ${l.result}</span>` : "";

    html += `
      <div style="margin-bottom:6px;border-bottom:1px solid #172554;padding-bottom:4px;">
        <span style="color:#64748B;">[${l.timestamp}]</span>
        <span style="color:${levelColor};font-weight:700;margin:0 6px;">[${l.level}]</span>
        <span style="color:#E2E8F0;font-weight:600;">[${l.agent_name || 'System'}]</span>
        <span style="color:#CBD5E1;margin-left:6px;">${escapeHtml(l.activity)}</span>
        ${resultText}
        ${latencyText}
      </div>
    `;
  });

  terminal.innerHTML = html;
}

function updateAgentCards(logs) {
  const agentMap = {
    "Coordinator Agent": "coordinator",
    "Diagnosis Agent": "diagnosis",
    "Troubleshooting Agent": "troubleshooting",
    "Monitoring Agent": "monitoring",
    "Escalation Agent": "escalation"
  };

  const latestPerAgent = {};
  logs.forEach(l => {
    if (l.agent_name && !latestPerAgent[l.agent_name]) {
      latestPerAgent[l.agent_name] = l;
    }
  });

  Object.keys(agentMap).forEach(agentName => {
    const key = agentMap[agentName];
    const card = document.getElementById(`card-agent-${key}`);
    if (card) {
      const actEl = card.querySelector(".agent-last-act");
      if (latestPerAgent[agentName] && actEl) {
        actEl.textContent = latestPerAgent[agentName].activity.substring(0, 36) + (latestPerAgent[agentName].activity.length > 36 ? "..." : "");
      }
    }
  });
}

async function clearTemporaryLogs() {
  if (!confirm("Are you sure you want to clear the in-memory temporary log buffer?")) return;
  try {
    await fetch("/api/monitoring/logs/clear", { method: "POST" });
    fetchLogs();
  } catch (err) {
    alert("Failed to clear temporary logs: " + err);
  }
}

function toggleAutoRefresh() {
  isAutoRefreshActive = !isAutoRefreshActive;
  const btn = document.getElementById("btn-auto-refresh");
  if (!btn) return;
  if (isAutoRefreshActive) {
    btn.textContent = "Auto-Refresh: Active";
    btn.style.color = "#38BDF8";
    startPolling();
  } else {
    btn.textContent = "Auto-Refresh: Paused";
    btn.style.color = "#94A3B8";
    stopPolling();
  }
}

function startPolling() {
  stopPolling();
  autoRefreshInterval = setInterval(() => {
    fetchServerStatus();
    fetchLogs();
  }, 3000);
}

function stopPolling() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
}

function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

document.addEventListener("DOMContentLoaded", () => {
  fetchServerStatus();
  fetchLogs();
  startPolling();
});
