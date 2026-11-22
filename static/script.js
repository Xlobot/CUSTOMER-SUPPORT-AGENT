/* ═══════════════════════════════════════════════════════
   NetCare AI — script.js
   All frontend logic: API calls, chat, tabs, dashboard
═══════════════════════════════════════════════════════ */

"use strict";

// ─────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────

const state = {
  sessionId: null,
  currentAction: null,
  currentScenario: "router_disconnected",
  customerId: null,
  sessionStatus: null,   // 'in_progress' | 'resolved' | 'escalated'
};

// ─────────────────────────────────────────────
// UTILS
// ─────────────────────────────────────────────

async function api(path, method = "GET", body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}

function toast(msg, duration = 3000) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.style.display = "block";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.style.display = "none"; }, duration);
}

function fmtTime(ts) {
  if (!ts) return "";
  const d = new Date(ts.replace(" ", "T") + "Z");
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtDateTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts.replace(" ", "T") + "Z");
  return d.toLocaleString();
}

function priorityPill(p) {
  const cls = { High: "pill-high", Medium: "pill-medium", Low: "pill-low" };
  return `<span class="pill ${cls[p] || 'pill-medium'}">${p || "Medium"}</span>`;
}

function statusPill(s) {
  const cls = { Open: "pill-open", Closed: "pill-closed", resolved: "pill-resolved", escalated: "pill-escalated", open: "pill-open" };
  return `<span class="pill ${cls[s] || 'pill-open'}">${s}</span>`;
}

function scrollChat() {
  const win = document.getElementById("chat-window");
  if (win) win.scrollTop = win.scrollHeight;
}

// ─────────────────────────────────────────────
// TABS
// ─────────────────────────────────────────────

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    // Reload data for certain tabs
    if (btn.dataset.tab === "dashboard") loadDashboard();
    if (btn.dataset.tab === "tickets") loadTickets();
    if (btn.dataset.tab === "cases") loadCases();
    if (btn.dataset.tab === "agents" && state.sessionId) loadAgentLog();
  });
});

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", async () => {
  await loadDashboard();
  await loadCustomerDropdown();
  await loadTickets();
  await loadCases();
  await loadModels();

  // Scenario dropdown sync
  const scenSelect = document.getElementById("scenario-select");
  scenSelect.addEventListener("change", () => {
    state.currentScenario = scenSelect.value;
  });

  // Enter key on chat message triggers sendChatMessage
  const chatInput = document.getElementById("chat-message");
  if (chatInput) {
    chatInput.addEventListener("keydown", e => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendChatMessage();
      }
    });
  }
});

// ─────────────────────────────────────────────
// HEALTH / GEMINI BADGE
// ─────────────────────────────────────────────

async function checkHealth() {
  try {
    const data = await api("/api/health");
    const activeModel = data.active_model || "gemini-3.5-flash";
    updateModelBadge(data.gemini_active, activeModel);
    const headerSel = document.getElementById("header-model-select");
    const demoSel = document.getElementById("demo-model-select");
    if (headerSel) headerSel.value = activeModel;
    if (demoSel) demoSel.value = activeModel;
  } catch { /* ignore */ }
}

// ─────────────────────────────────────────────
// MODEL MANAGEMENT & TEST
// ─────────────────────────────────────────────

async function loadModels() {
  try {
    const data = await api("/api/models");
    const activeModel = data.active_model || "gemini-3.5-flash";
    const headerSel = document.getElementById("header-model-select");
    const demoSel = document.getElementById("demo-model-select");
    if (headerSel) headerSel.value = activeModel;
    if (demoSel) demoSel.value = activeModel;
    updateModelBadge(data.gemini_active, activeModel);
  } catch (err) {
    console.error("loadModels error", err);
  }
}

async function switchModel(modelId) {
  try {
    const headerSel = document.getElementById("header-model-select");
    const demoSel = document.getElementById("demo-model-select");
    if (headerSel) headerSel.value = modelId;
    if (demoSel) demoSel.value = modelId;

    const res = await api("/api/models/select", "POST", { model: modelId });
    updateModelBadge(res.gemini_active, modelId);
    toast(`Switched AI Model to: ${modelId}`);
  } catch (err) {
    toast(`Failed to switch model: ${err.message}`);
  }
}

function updateModelBadge(isActive, modelId) {
  const badge = document.getElementById("gemini-badge");
  if (!badge) return;
  if (isActive && modelId !== "fallback") {
    const shortName = modelId.replace("gemini-", "Gemini ").replace("netcare-ft-local", "NetCare Local AI");
    badge.innerHTML = `<span class="status-dot"></span> ${shortName}`;
    badge.className = "badge badge-active";
  } else {
    badge.innerHTML = `<span class="status-dot"></span> Offline Fallback`;
    badge.className = "badge badge-fallback";
  }
}

async function testActiveModel() {
  const btnHeader = document.getElementById("btn-ping-header");
  const btnDemo = document.getElementById("btn-test-model");
  const resultDiv = document.getElementById("model-test-result");
  const headerSel = document.getElementById("header-model-select");
  const selectedModel = headerSel ? headerSel.value : "gemini-3.5-flash";

  if (btnHeader) btnHeader.disabled = true;
  if (btnDemo) btnDemo.disabled = true;
  toast(`Testing model latency: ${selectedModel}…`);

  try {
    const data = await api("/api/models/test", "POST", { model: selectedModel });
    if (resultDiv) {
      resultDiv.style.display = "block";
      if (data.status === "ok") {
        resultDiv.innerHTML = `
          <div style="color:var(--positive);font-weight:600;margin-bottom:4px;">
            Model Test Succeeded: <strong>${data.model}</strong>
          </div>
          <div><strong>Latency:</strong> ${data.latency_ms} ms</div>
          <div style="margin-top:6px;background:white;border:1px solid var(--border);border-radius:var(--radius-control);padding:8px;font-family:'JetBrains Mono',monospace;font-size:12px;">
            "${escapeHtml(data.sample_response)}"
          </div>
        `;
      } else {
        resultDiv.innerHTML = `
          <div style="color:var(--negative);font-weight:600;margin-bottom:4px;">
            Model Test Error: <strong>${data.model}</strong>
          </div>
          <div style="color:var(--negative);font-size:12px;">${escapeHtml(data.error || "Unknown error")}</div>
        `;
      }
    }
    toast(data.status === "ok" ? `${data.model} responded in ${data.latency_ms}ms` : `Model test failed`);
  } catch (err) {
    toast(`Test failed: ${err.message}`);
  } finally {
    if (btnHeader) btnHeader.disabled = false;
    if (btnDemo) btnDemo.disabled = false;
  }
}

// ─────────────────────────────────────────────
// DASHBOARD
// ─────────────────────────────────────────────

async function loadDashboard() {
  try {
    const data = await api("/api/dashboard");

    document.getElementById("stat-total").textContent = data.total_sessions ?? 0;
    document.getElementById("stat-resolved").textContent = data.resolved_cases ?? 0;
    document.getElementById("stat-tickets").textContent = data.open_tickets ?? 0;
    document.getElementById("stat-rate").textContent = (data.resolution_rate ?? 0) + "%";

    // Gemini badge
    const badge = document.getElementById("gemini-badge");
    if (data.gemini_active) {
      badge.innerHTML = `<span class="status-dot"></span> NetCare AI Active`;
      badge.className = "badge badge-active";
    } else {
      badge.innerHTML = `<span class="status-dot"></span> Fallback Mode`;
      badge.className = "badge badge-fallback";
    }

    // Recent tickets
    const tEl = document.getElementById("dash-tickets");
    if (!data.recent_tickets?.length) {
      tEl.innerHTML = '<div class="log-placeholder">No tickets yet.</div>';
    } else {
      tEl.innerHTML = data.recent_tickets.map(t => `
        <div style="padding:10px 0;border-bottom:1px solid #F1F5F9;font-size:12px;">
          <strong style="font-family:monospace;color:var(--danger)">${t.ticket_id}</strong>
          <span style="margin-left:8px">${t.customer_name || t.customer_id}</span>
          ${priorityPill(t.priority)}
          <div style="color:var(--text-muted);margin-top:2px">${t.issue_description}</div>
        </div>
      `).join("");
    }

    // Recent resolved cases
    const cEl = document.getElementById("dash-cases");
    if (!data.recent_cases?.length) {
      cEl.innerHTML = '<div class="log-placeholder">No resolved cases yet.</div>';
    } else {
      cEl.innerHTML = data.recent_cases.map(c => `
        <div style="padding:10px 0;border-bottom:1px solid #F1F5F9;font-size:12px;">
          <strong>${c.customer_name || c.customer_id}</strong>
          <div style="color:var(--text-muted)">${c.symptoms}</div>
          <div>Resolved by: <span style="color:var(--positive)">${c.successful_action}</span></div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Dashboard error", err);
  }
}

// ─────────────────────────────────────────────
// CUSTOMER DROPDOWN
// ─────────────────────────────────────────────

async function loadCustomerDropdown() {
  try {
    const customers = await api("/api/customers");
    const sel = document.getElementById("customer-select");
    customers.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.customer_id;
      opt.textContent = `${c.customer_id} — ${c.name} (${c.plan})`;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => {
      if (sel.value) document.getElementById("customer-id-input").value = sel.value;
    });
  } catch (err) { console.error(err); }
}

// ─────────────────────────────────────────────
// LOAD CUSTOMER
// ─────────────────────────────────────────────

async function loadCustomer() {
  const idEl = document.getElementById("customer-id-input");
  const selEl = document.getElementById("customer-select");
  const cid = (idEl.value.trim() || selEl.value).toUpperCase();
  if (!cid) { toast("Please select or enter a customer ID."); return; }

  try {
    const c = await api("/api/customer/" + cid);
    if (c.error) { toast(c.error); return; }

    state.customerId = c.customer_id;
    document.getElementById("customer-id-input").value = c.customer_id;

    const infoEl = document.getElementById("customer-info");
    const statusColor = c.account_status === "Active" ? "var(--positive)" : "var(--negative)";
    infoEl.innerHTML = `
      <div class="cust-name">${c.name}</div>
      <div class="customer-detail">
        <div class="cust-field"><div class="cust-label">Customer ID</div><div class="cust-value">${c.customer_id}</div></div>
        <div class="cust-field"><div class="cust-label">Status</div><div class="cust-value" style="color:${statusColor}">${c.account_status}</div></div>
        <div class="cust-field"><div class="cust-label">Plan</div><div class="cust-value">${c.plan}</div></div>
        <div class="cust-field"><div class="cust-label">Member Since</div><div class="cust-value">${c.joined_date}</div></div>
        <div class="cust-field"><div class="cust-label">Email</div><div class="cust-value">${c.email}</div></div>
        <div class="cust-field"><div class="cust-label">Phone</div><div class="cust-value">${c.phone}</div></div>
      </div>
      <div style="margin-top:10px;font-size:12px;color:var(--text-muted)">Location: ${c.address}</div>
    `;
    document.getElementById("customer-card").style.display = "block";
    toast(`Account loaded: ${c.name}`);
  } catch (err) {
    toast("Error loading customer: " + err.message);
  }
}

// ─────────────────────────────────────────────
// START SESSION
// ─────────────────────────────────────────────

async function startSession() {
  const initialInput = document.getElementById("initial-issue-input");
  const chatInput = document.getElementById("chat-message");
  const msg = (initialInput && initialInput.value.trim()) ||
    (chatInput && chatInput.value.trim()) ||
    "My internet has stopped working. Help me fix it.";
  const cid = document.getElementById("customer-id-input").value.trim().toUpperCase() ||
    document.getElementById("customer-select").value;
  const scenario = document.getElementById("scenario-select").value;

  if (!cid) {
    toast("Please select or enter a customer ID first.");
    document.getElementById("nav-support").click();
    return;
  }

  // Clear chat
  const chatWin = document.getElementById("chat-window");
  chatWin.innerHTML = '<div class="msg-system">Initializing troubleshooting session…</div>';
  document.getElementById("feedback-row").style.display = "none";
  const startBtn = document.getElementById("btn-start");
  if (startBtn) startBtn.disabled = true;

  try {
    const data = await api("/api/session/start", "POST", {
      customer_id: cid, message: msg, scenario,
    });

    if (data.error) {
      chatWin.innerHTML = `<div class="msg-system" style="color:var(--negative)">${data.error}</div>`;
      if (startBtn) startBtn.disabled = false;
      return;
    }

    state.sessionId = data.session_id;
    state.currentScenario = scenario;
    state.sessionStatus = "in_progress";
    state.currentAction = data.next_action?.action;

    // Show session badge
    const badge = document.getElementById("session-badge");
    if (badge) {
      badge.textContent = state.sessionId.slice(0, 8).toUpperCase();
      badge.style.display = "inline";
    }

    // Show New Session button
    const newBtn = document.getElementById("btn-new-session");
    if (newBtn) newBtn.style.display = "block";

    // Customer card
    if (data.customer) {
      const c = data.customer;
      const infoEl = document.getElementById("customer-info");
      const statusColor = c.account_status === "Active" ? "var(--success)" : "var(--danger)";
      infoEl.innerHTML = `
        <div class="cust-name">${c.name}</div>
        <div class="customer-detail">
          <div class="cust-field"><div class="cust-label">ID</div><div class="cust-value">${c.customer_id}</div></div>
          <div class="cust-field"><div class="cust-label">Status</div><div class="cust-value" style="color:${statusColor}">${c.account_status}</div></div>
          <div class="cust-field"><div class="cust-label">Plan</div><div class="cust-value">${c.plan}</div></div>
          <div class="cust-field"><div class="cust-label">Phone</div><div class="cust-value">${c.phone}</div></div>
        </div>`;
      document.getElementById("customer-card").style.display = "block";
    }

    // Diagnosis card
    if (data.diagnosis) {
      const d = data.diagnosis;
      const checksHtml = d.checks?.map(ch => {
        const ok = ch.result === "OK" || ch.result === "Up";
        return `<li><span class="${ok ? 'check-ok' : 'check-fail'}">${ok ? '✓' : '✗'}</span> ${ch.check}: <strong>${ch.result}</strong></li>`;
      }).join("") || "";
      document.getElementById("diag-content").innerHTML = `
        <div style="margin-bottom:8px"><strong>${d.label}</strong> — Severity: ${priorityPill(d.severity)}</div>
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">${d.diagnosis}</p>
        <ul class="diag-checks">${checksHtml}</ul>
      `;
      document.getElementById("diag-card").style.display = "block";
    }

    // Past case
    if (data.past_case) {
      const pc = data.past_case;
      document.getElementById("past-case-content").innerHTML = `
        <p style="font-size:12px;color:var(--text-muted)">A similar past case was found and used to prioritise recommendations:</p>
        <div style="background:#F0FDF4;border:1px solid #A7F3D0;border-radius:8px;padding:10px;margin-top:8px;font-size:12px">
          <strong>Symptoms:</strong> ${pc.symptoms}<br>
          <strong>Diagnosis:</strong> ${pc.diagnosis}<br>
          <strong>Resolved by:</strong> <span style="color:var(--success)">${pc.successful_action}</span>
        </div>`;
      document.getElementById("past-case-card").style.display = "block";
    }

    // Add customer message bubble
    chatWin.innerHTML = "";
    addMessage(msg, "customer");

    // Add agent welcome message
    if (data.welcome_message) addMessage(data.welcome_message, "agent", "", data.model_used || "NetCare Model");

    // Add first troubleshooting instruction
    if (data.next_action) {
      addSystemMessage("Stage: ACT — Recommending remediation step");
      addMessage(
        `Remediation Step: ${data.next_action.label}\n\n${data.next_action.instructions}`,
        "agent"
      );
      setStage("ACT", "Agent recommending: " + data.next_action.label);
      document.getElementById("feedback-row").style.display = "flex";
    }

    if (chatInput) chatInput.value = "";
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = "Restart Support Session";
    }
    scrollChat();
    updateAgentStatuses("active");

    // Load agent log
    setTimeout(loadAgentLog, 500);

  } catch (err) {
    chatWin.innerHTML = `<div class="msg-system" style="color:var(--negative)">Error: ${err.message}</div>`;
    if (startBtn) startBtn.disabled = false;
  }
}

// ─────────────────────────────────────────────
// CONVERSATIONAL CHAT (IN SAME SESSION)
// ─────────────────────────────────────────────

async function sendChatMessage() {
  const msgEl = document.getElementById("chat-message");
  const text = msgEl.value.trim();
  if (!text) return;

  const chatWin = document.getElementById("chat-window");
  const sendBtn = document.getElementById("btn-send");

  // 1. If NO session is active yet, interact dynamically via /api/chat
  if (!state.sessionId || state.sessionStatus === "resolved" || state.sessionStatus === "escalated") {
    // If chat-welcome is still visible, clear it out for live chat
    const welcome = chatWin.querySelector(".chat-welcome");
    if (welcome) chatWin.innerHTML = "";

    addMessage(text, "customer");
    msgEl.value = "";
    msgEl.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
    scrollChat();

    // Show thinking indicator
    const typingEl = document.createElement("div");
    typingEl.id = "chat-thinking-indicator";
    typingEl.className = "msg msg-agent";
    typingEl.innerHTML = `
      <span class="msg-avatar">AI</span>
      <span class="msg-bubble" style="opacity:0.75;font-style:italic">Evaluating message…</span>
    `;
    chatWin.appendChild(typingEl);
    scrollChat();

    try {
      const cid = (document.getElementById("customer-id-input").value.trim() ||
                   document.getElementById("customer-select").value || "NET1001").toUpperCase();
      const scenario = document.getElementById("scenario-select").value || "router_disconnected";

      const data = await api("/api/chat", "POST", { customer_id: cid, message: text, scenario });
      const ind = document.getElementById("chat-thinking-indicator");
      if (ind) ind.remove();

      if (data.session_id) {
        // Genuine problem report recognized: initialize full diagnostic session
        state.sessionId       = data.session_id;
        state.currentScenario = scenario;
        state.sessionStatus   = "in_progress";
        state.currentAction   = data.next_action?.action;

        const badge = document.getElementById("session-badge");
        if (badge) {
          badge.textContent = state.sessionId.slice(0, 8).toUpperCase();
          badge.style.display = "inline";
        }
        const newBtn = document.getElementById("btn-new-session");
        if (newBtn) newBtn.style.display = "block";

        // Update customer card
        if (data.customer) {
          const c = data.customer;
          const infoEl = document.getElementById("customer-info");
          const statusColor = c.account_status === "Active" ? "var(--positive)" : "var(--negative)";
          infoEl.innerHTML = `
            <div class="cust-name">${c.name}</div>
            <div class="customer-detail">
              <div class="cust-field"><div class="cust-label">ID</div><div class="cust-value">${c.customer_id}</div></div>
              <div class="cust-field"><div class="cust-label">Status</div><div class="cust-value" style="color:${statusColor}">${c.account_status}</div></div>
              <div class="cust-field"><div class="cust-label">Plan</div><div class="cust-value">${c.plan}</div></div>
              <div class="cust-field"><div class="cust-label">Phone</div><div class="cust-value">${c.phone}</div></div>
            </div>`;
          document.getElementById("customer-card").style.display = "block";
        }

        // Update diagnosis card
        if (data.diagnosis) {
          const d = data.diagnosis;
          const checksHtml = d.checks?.map(ch => {
            const ok = ch.status === "PASS" || ch.result === "OK" || ch.result === "Up";
            return `<li><span class="${ok ? 'check-ok' : 'check-fail'}">${ok ? '✓' : '✗'}</span> ${ch.check}: <strong>${ch.status || ch.result}</strong></li>`;
          }).join("") || "";
          document.getElementById("diag-content").innerHTML = `
            <div style="margin-bottom:8px"><strong>${d.label}</strong> — Severity: ${priorityPill(d.severity)}</div>
            <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">${d.diagnosis}</p>
            <ul class="diag-checks">${checksHtml}</ul>
          `;
          document.getElementById("diag-card").style.display = "block";
        }

        // Update past case card
        if (data.past_case) {
          const pc = data.past_case;
          document.getElementById("past-case-content").innerHTML = `
            <p style="font-size:12px;color:var(--text-muted)">A similar past case was found and used to prioritise recommendations:</p>
            <div style="background:#F0FDF4;border:1px solid #A7F3D0;border-radius:8px;padding:10px;margin-top:8px;font-size:12px">
              <strong>Symptoms:</strong> ${pc.symptoms}<br>
              <strong>Diagnosis:</strong> ${pc.diagnosis}<br>
              <strong>Resolved by:</strong> <span style="color:var(--positive)">${pc.successful_action}</span>
            </div>`;
          document.getElementById("past-case-card").style.display = "block";
        }

        if (data.welcome_message) addMessage(data.welcome_message, "agent", "", data.model_used || "NetCare Model");
        if (data.next_action) {
          addSystemMessage("Stage: ACT — Recommending remediation step");
          addMessage(
            `Remediation Step: ${data.next_action.label}\n\n${data.next_action.instructions}`,
            "agent"
          );
          setStage("ACT", "Agent recommending: " + data.next_action.label);
          document.getElementById("feedback-row").style.display = "flex";
        }
        updateAgentStatuses("active");
        setTimeout(loadAgentLog, 500);
      } else {
        // Dynamic conversational response (greetings, gibberish, questions, identity)
        const replyText = data.reply || data.welcome_message || data.message || "I have received your message. How can I help you troubleshoot your connection today?";
        addMessage(replyText, "agent", "", data.model_used || "NetCare Model");
      }
    } catch (err) {
      const ind = document.getElementById("chat-thinking-indicator");
      if (ind) ind.remove();
      addSystemMessage(`Error: ${err.message}`);
    } finally {
      msgEl.disabled = false;
      if (sendBtn) sendBtn.disabled = false;
      msgEl.focus();
      scrollChat();
    }
    return;
  }

  // 2. Active Session Chat
  addMessage(text, "customer");
  msgEl.value = "";
  msgEl.disabled = true;
  if (sendBtn) sendBtn.disabled = true;
  scrollChat();

  // Add animated thinking indicator
  const typingEl = document.createElement("div");
  typingEl.id = "chat-thinking-indicator";
  typingEl.className = "msg msg-agent";
  typingEl.innerHTML = `
    <span class="msg-avatar">AI</span>
    <span class="msg-bubble" style="opacity:0.75;font-style:italic">Evaluating diagnostic context…</span>
  `;
  chatWin.appendChild(typingEl);
  scrollChat();

  try {
    const data = await api(`/api/session/${state.sessionId}/message`, "POST", { message: text });

    // Remove thinking indicator
    const ind = document.getElementById("chat-thinking-indicator");
    if (ind) ind.remove();

    if (data.error) {
      addSystemMessage(`${data.error}`);
    } else if (data.status === "resolved") {
      handleResolved(data);
    } else if (data.status === "escalated") {
      handleEscalated(data);
    } else if (data.intent === "adjusted") {
      handleAdjust(data);
    } else {
      // Intelligent dynamic conversational reply
      const replyText = data.reply || data.message || "Diagnostic update received.";
      addMessage(replyText, "agent", "", data.model_used || "NetCare Model");
    }

    setTimeout(loadAgentLog, 400);
    loadDashboard();
  } catch (err) {
    const ind = document.getElementById("chat-thinking-indicator");
    if (ind) ind.remove();
    addSystemMessage(`Error: ${err.message}`);
  } finally {
    msgEl.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
    msgEl.focus();
    scrollChat();
  }
}

function resetActiveSession() {
  state.sessionId = null;
  state.currentAction = null;
  state.sessionStatus = null;
  const badge = document.getElementById("session-badge");
  if (badge) badge.style.display = "none";
  const newBtn = document.getElementById("btn-new-session");
  if (newBtn) newBtn.style.display = "none";
  const startBtn = document.getElementById("btn-start");
  if (startBtn) {
    startBtn.disabled = false;
    startBtn.textContent = "Start Support Session";
  }
  document.getElementById("feedback-row").style.display = "none";
  document.getElementById("diag-card").style.display = "none";
  document.getElementById("past-case-card").style.display = "none";
  const chatWin = document.getElementById("chat-window");
  chatWin.innerHTML = `
    <div class="chat-welcome">
      <h3>Ready for Support Session</h3>
      <p>Select a customer account and scenario on the left, then click <strong>Start Support Session</strong>.</p>
    </div>
  `;
  setStage("ACT", "Ready to start troubleshooting.");
  toast("New session ready. Choose customer & scenario to start.");
}

// ─────────────────────────────────────────────
// FEEDBACK
// ─────────────────────────────────────────────

async function submitFeedback(feedbackType) {
  if (!state.sessionId || !state.currentAction) {
    toast("No active session."); return;
  }
  if (state.sessionStatus !== "in_progress") {
    toast("This session has already ended."); return;
  }

  // Disable buttons temporarily
  document.querySelectorAll(".feedback-row .btn").forEach(b => b.disabled = true);

  // Show observe stage
  setStage("OBSERVE", `Customer reported: "${feedbackType.replace("_", " ")}" — Monitoring agent observing…`);
  addSystemMessage("Stage: OBSERVE — Monitoring Agent evaluating feedback…");

  try {
    const data = await api(`/api/session/${state.sessionId}/feedback`, "POST", {
      action: state.currentAction,
      feedback: feedbackType,
      scenario: state.currentScenario,
    });

    // REFLECT stage
    setTimeout(() => {
      setStage("REFLECT", data.adaptation?.reflection || "Reflecting on outcome…");
      addSystemMessage("Stage: REFLECT — " + (data.adaptation?.reflection || "Analysing result…"));
    }, 800);

    setTimeout(() => {
      if (data.status === "resolved") {
        handleResolved(data);
      } else if (data.status === "escalated") {
        handleEscalated(data);
      } else {
        handleAdjust(data);
      }
      setTimeout(loadAgentLog, 500);
      loadDashboard();
    }, 1600);

  } catch (err) {
    toast("Error: " + err.message);
    document.querySelectorAll(".feedback-row .btn").forEach(b => b.disabled = false);
  }
}

function handleResolved(data) {
  state.sessionStatus = "resolved";
  setStage("RESOLVED", "Issue resolved! Case closed and saved.");
  document.getElementById("feedback-row").style.display = "none";
  addSystemMessage("Status: RESOLVED — Issue resolved and recorded to case memory");
  addMessage(data.message, "agent", "msg-resolved");
  updateAgentStatuses("done");
  toast("Issue resolved successfully.");
  loadCases();
}

function handleEscalated(data) {
  state.sessionStatus = "escalated";
  setStage("ESCALATED", "Escalated — Support ticket created.");
  document.getElementById("feedback-row").style.display = "none";
  addSystemMessage("Status: ESCALATED — Support ticket created");
  addMessage(data.message, "agent", "msg-ticket");
  if (data.ticket) {
    addTicketCard(data.ticket);
  }
  updateAgentStatuses("done");
  toast("Ticket created: " + (data.ticket?.ticket_id || ""));
  loadTickets();
}

function handleAdjust(data) {
  setStage("ADJUST", "Selecting next troubleshooting action…");
  addSystemMessage("Stage: ADJUST — Agent selecting alternative action");
  addMessage(data.message, "agent");

  if (data.next_action) {
    state.currentAction = data.next_action.action;
    addSystemMessage("Stage: ACT — Recommending: " + data.next_action.label);
    setStage("ACT", "Agent recommending: " + data.next_action.label);
  }

  document.querySelectorAll(".feedback-row .btn").forEach(b => b.disabled = false);
  scrollChat();
}

// ─────────────────────────────────────────────
// CHAT HELPERS
// ─────────────────────────────────────────────

function addMessage(text, sender, extraClass = "", modelBadge = "") {
  if (text === undefined || text === null || !String(text).trim()) return;
  const chatWin = document.getElementById("chat-window");
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const isAgent = sender === "agent";
  const badgeHtml = isAgent && modelBadge ? `<span class="badge" style="background:var(--bg-raised);color:var(--text-secondary);border:1px solid var(--border);font-family:'JetBrains Mono',monospace;">${escapeHtml(modelBadge)}</span>` : "";

  const div = document.createElement("div");
  div.className = `msg msg-${sender} ${extraClass}`;
  div.innerHTML = `
    <div class="msg-avatar">${isAgent ? "AI" : "User"}</div>
    <div>
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-time">${isAgent ? "NetCare AI" : "You"} · ${now} ${badgeHtml}</div>
    </div>
  `;
  chatWin.appendChild(div);
  scrollChat();
}

function addSystemMessage(text) {
  const chatWin = document.getElementById("chat-window");
  const div = document.createElement("div");
  div.className = "msg-system";
  div.textContent = text;
  chatWin.appendChild(div);
  scrollChat();
}

function addTicketCard(ticket) {
  const chatWin = document.getElementById("chat-window");
  const div = document.createElement("div");
  div.className = "msg msg-agent";
  div.innerHTML = `
    <div class="msg-avatar">TKT</div>
    <div>
      <div class="msg-bubble" style="background:var(--negative-light);border:1px solid var(--negative-border);">
        <div class="ticket-id">${ticket.ticket_id}</div>
        <div style="font-size:12px">
          <strong>Priority:</strong> ${ticket.priority}<br>
          <strong>Reason:</strong> ${ticket.reason}<br>
          <strong>Steps Tried:</strong> ${ticket.steps_attempted || "None"}
        </div>
      </div>
      <div class="msg-time">Escalation Agent · Support Ticket</div>
    </div>
  `;
  chatWin.appendChild(div);
  scrollChat();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");
}

// ─────────────────────────────────────────────
// STAGE INDICATOR
// ─────────────────────────────────────────────

function setStage(stage, description) {
  const pills = ["ACT", "OBSERVE", "REFLECT", "ADJUST"];
  const specialStages = ["RESOLVED", "ESCALATED"];
  const stageOrder = { ACT: 0, OBSERVE: 1, REFLECT: 2, ADJUST: 3 };
  const currentIdx = stageOrder[stage] ?? -1;

  pills.forEach((s, i) => {
    const el = document.getElementById("stage-" + s.toLowerCase());
    if (!el) return;
    el.classList.remove("active", "done");
    if (specialStages.includes(stage)) {
      el.classList.add("done");
    } else if (i < currentIdx) {
      el.classList.add("done");
    } else if (i === currentIdx) {
      el.classList.add("active");
    }
  });

  document.getElementById("stage-description").textContent = description || "";
}

// ─────────────────────────────────────────────
// AGENT LOG
// ─────────────────────────────────────────────

async function loadAgentLog() {
  if (!state.sessionId) return;
  try {
    const data = await api(`/api/session/${state.sessionId}`);
    const logs = data.agent_logs || [];

    document.getElementById("session-log-label").textContent =
      "Session: " + state.sessionId.slice(0, 8).toUpperCase();

    if (!logs.length) {
      document.getElementById("agent-log-table").innerHTML =
        '<div class="log-placeholder">No agent activity yet.</div>';
      return;
    }

    const rows = logs.map(l => `
      <tr>
        <td><strong>${l.agent_name}</strong></td>
        <td>${l.activity}</td>
        <td>${l.result || "—"}</td>
        <td style="color:var(--text-muted)">${fmtTime(l.timestamp)}</td>
      </tr>
    `).join("");

    document.getElementById("agent-log-table").innerHTML = `
      <table class="log-table">
        <thead><tr>
          <th>Agent</th><th>Activity</th><th>Result</th><th>Time</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (err) { console.error(err); }
}

// ─────────────────────────────────────────────
// AGENT STATUSES
// ─────────────────────────────────────────────

function updateAgentStatuses(status) {
  const agentMap = {
    coordinator: "Coordinator Agent",
    diagnosis: "Diagnosis Agent",
    troubleshoot: "Troubleshooting Agent",
    monitor: "Monitoring Agent",
    escalation: "Escalation Agent",
  };
  Object.keys(agentMap).forEach(key => {
    const el = document.getElementById("status-" + key);
    if (!el) return;
    if (status === "active") {
      el.className = "agent-status active";
      el.textContent = "Active";
    } else if (status === "done") {
      el.className = "agent-status done";
      el.textContent = "Completed";
    }
  });
}

// ─────────────────────────────────────────────
// TICKETS
// ─────────────────────────────────────────────

async function loadTickets() {
  try {
    const tickets = await api("/api/tickets");
    const el = document.getElementById("tickets-table");

    if (!tickets.length) {
      el.innerHTML = '<div class="log-placeholder">No tickets yet. Tickets are created when troubleshooting fails.</div>';
      return;
    }

    const rows = tickets.map(t => `
      <tr>
        <td><strong style="font-family:monospace;color:var(--danger)">${t.ticket_id}</strong></td>
        <td>${t.customer_name || t.customer_id}</td>
        <td>${t.issue_description}</td>
        <td>${priorityPill(t.priority)}</td>
        <td>${statusPill(t.status)}</td>
        <td style="color:var(--text-muted)">${fmtDateTime(t.created_at)}</td>
      </tr>
    `).join("");

    el.innerHTML = `
      <table class="log-table">
        <thead><tr>
          <th>Ticket ID</th><th>Customer</th><th>Issue</th>
          <th>Priority</th><th>Status</th><th>Created</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (err) { console.error(err); }
}

// ─────────────────────────────────────────────
// PREVIOUS CASES
// ─────────────────────────────────────────────

async function loadCases() {
  try {
    const cases = await api("/api/cases");
    renderCases(cases, document.getElementById("cases-table"));
  } catch (err) { console.error(err); }
}

async function searchCases() {
  const q = document.getElementById("case-search-input").value.trim();
  if (!q) { document.getElementById("search-results").innerHTML = ""; return; }
  try {
    const cases = await api("/api/cases/search?q=" + encodeURIComponent(q));
    const el = document.getElementById("search-results");
    if (!cases.length) {
      el.innerHTML = '<div class="log-placeholder">No matching cases found.</div>';
      return;
    }
    el.innerHTML = "<h4 style='margin-bottom:10px;color:var(--primary)'>Search Results (" + cases.length + " found)</h4>";
    renderCases(cases, el, true);
  } catch (err) { console.error(err); }
}

function renderCases(cases, container, append = false) {
  if (!cases.length) {
    container.innerHTML = '<div class="log-placeholder">No resolved cases yet. Cases are saved when troubleshooting succeeds.</div>';
    return;
  }
  const rows = cases.map(c => `
    <tr>
      <td>#${c.case_id}</td>
      <td>${c.customer_name || c.customer_id}</td>
      <td>${c.symptoms}</td>
      <td>${c.diagnosis}</td>
      <td style="color:var(--success)"><strong>${c.successful_action}</strong></td>
      <td style="color:var(--text-muted)">${fmtDateTime(c.resolved_at)}</td>
    </tr>
  `).join("");

  const table = `
    <table class="log-table">
      <thead><tr>
        <th>#</th><th>Customer</th><th>Symptoms</th>
        <th>Diagnosis</th><th>Resolved By</th><th>Date</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;

  if (append) {
    container.innerHTML += table;
  } else {
    container.innerHTML = table;
  }
}

// ─────────────────────────────────────────────
// DEMO CONTROLS
// ─────────────────────────────────────────────

async function resetDemo() {
  if (!confirm("Reset all demo data? Customer accounts will be preserved.")) return;
  try {
    const data = await api("/api/demo/reset", "POST");
    const el = document.getElementById("reset-message");
    el.textContent = data.message;
    el.style.display = "block";
    // Reset state
    state.sessionId = null;
    state.currentAction = null;
    state.sessionStatus = null;
    setTimeout(() => { el.style.display = "none"; }, 4000);
    loadDashboard();
    loadTickets();
    loadCases();
    toast("Demo data reset successfully.");
  } catch (err) {
    toast("Reset failed: " + err.message);
  }
}

function quickLaunch(customerId, scenario) {
  // Set up the support tab with pre-selected values
  document.getElementById("customer-id-input").value = customerId;
  document.getElementById("scenario-select").value = scenario;
  state.currentScenario = scenario;
  document.getElementById("chat-message").value = "My internet is not working.";
  // Switch to support tab
  document.getElementById("nav-support").click();
  toast(`Loaded customer ${customerId} with scenario ${scenario}`);
}

// Scenario 1: Quick resolution
function runScenario1() {
  quickLaunch("NET1001", "resolved_quickly");
}

// Scenario 2: Feedback-based adaptation
function runScenario2() {
  quickLaunch("NET1002", "router_disconnected");
}

// Scenario 3: Escalation
function runScenario3() {
  quickLaunch("NET1003", "isp_outage");
}
