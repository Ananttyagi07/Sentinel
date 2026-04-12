const API_BASE = "http://localhost:8000";

const state = {
  currentTab: "chat",
  pageInfo: { url: "", title: "", content: "" },
  chatHistory: [],
  isLoading: false,
  backendOnline: false,
  sessionId: crypto.randomUUID(),
};

document.getElementById("app").innerHTML = `
  <div class="header">
    <div class="logo">
      <div class="logo-icon">⬡</div>
      <span class="logo-text">SENTINEL</span>
    </div>
    <div class="status-block">
      <div id="status-dot" class="status-dot" title="Backend Status"></div>
      <span class="status-label" id="status-label">OFFLINE</span>
    </div>
  </div>

  <div class="page-bar">
    <span class="site-icon">↗</span>
    <span class="page-title" id="page-title">Loading page...</span>
  </div>

  <div class="tabs">
    <button class="tab-btn active" data-tab="chat">
      <span class="tab-icon">✦</span>CHAT
    </button>
    <button class="tab-btn" data-tab="research">
      <span class="tab-icon">◎</span>RESEARCH
    </button>
    <button class="tab-btn" data-tab="sync">
      <span class="tab-icon">□</span>NOTION
    </button>
  </div>

  <div class="panels">

    <!-- CHAT -->
    <div class="panel active" id="panel-chat">
      <div class="chat-messages" id="chat-messages">
        <div class="msg msg-agent">
          <div class="msg-label">SENTINEL</div>
          <div class="msg-bubble">Hello — I'm Sentinel. Ask me anything about this page, run deep research, or sync it to Notion.</div>
        </div>
      </div>
      <div class="chat-input-row">
        <textarea class="input" id="chat-input" rows="2" placeholder="Ask about this page..."></textarea>
        <button class="chat-send" id="chat-send">↑</button>
      </div>
    </div>

    <!-- RESEARCH -->
    <div class="panel" id="panel-research">
      <div class="card">
        <div class="card-title">◎ DEEP RESEARCH</div>
        <textarea class="input" id="research-query" rows="3" placeholder="What do you want to research? Sentinel will plan, search the live web, and synthesize findings..."></textarea>
        <div style="height:10px"></div>
        <button class="btn btn-primary" id="research-btn">RUN RESEARCH →</button>
      </div>
      <div id="research-log" style="display:none" class="agent-log">INITIALIZING AGENT...</div>
      <div id="research-result" style="display:none"></div>
    </div>

    <!-- NOTION SYNC -->
    <div class="panel" id="panel-sync">
      <div class="card">
        <div class="card-title">□ NOTION SYNC</div>
        <p style="color:#666;font-size:12px;font-family:var(--font-mono);line-height:1.6;margin-bottom:14px">
          Sentinel analyzes this page, extracts insights and tags, then writes it to your Notion database — structured and categorized.
        </p>
        <button class="btn btn-purple" id="sync-btn">SYNC TO NOTION →</button>
      </div>
      <div id="sync-result" style="display:none"></div>
    </div>

  </div>
`;

async function init() {
  await loadPageInfo();
  await checkBackendHealth();
  setupEventListeners();
}

async function loadPageInfo() {
  try {
    const info = await chrome.runtime.sendMessage({ type: "GET_PAGE_CONTENT" });
    state.pageInfo = info;
    const titleEl = document.getElementById("page-title");
    titleEl.textContent = info.title || info.url || "Unknown page";
    titleEl.title = info.url;
  } catch (e) {
    document.getElementById("page-title").textContent = "Unable to read page";
  }
}

async function checkBackendHealth() {
  try {
    const result = await chrome.runtime.sendMessage({ type: "CHECK_HEALTH" });
    state.backendOnline = result?.status === "online";
  } catch {
    state.backendOnline = false;
  }

  const dot = document.getElementById("status-dot");
  const label = document.getElementById("status-label");
  if (state.backendOnline) {
    dot.className = "status-dot online";
    label.textContent = "ONLINE";
  } else {
    dot.className = "status-dot";
    label.textContent = "OFFLINE";
  }
}

function setupEventListeners() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.currentTab = btn.dataset.tab;
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
    });
  });

  document.getElementById("chat-send").addEventListener("click", sendChat);
  document.getElementById("chat-input").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });

  document.getElementById("research-btn").addEventListener("click", runResearch);
  document.getElementById("sync-btn").addEventListener("click", runSync);
}

async function sendChat() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message || state.isLoading) return;

  state.isLoading = true;
  input.value = "";
  appendMessage("user", message);
  state.chatHistory.push({ role: "user", content: message });

  const loadingId = appendLoading();

  try {
    // Refresh page info before each request to get the current URL
    await loadPageInfo();
    const result = await chrome.runtime.sendMessage({
      type: "RUN_CHAT",
      payload: {
        url: state.pageInfo.url,
        page_content: state.pageInfo.content,
        message,
        history: state.chatHistory.slice(-8),
        session_id: state.sessionId,
      },
    });

    removeElement(loadingId);
    const response = result?.result || "Sorry, I couldn't get a response.";
    appendMessage("agent", response);
    state.chatHistory.push({ role: "assistant", content: response });
  } catch (e) {
    removeElement(loadingId);
    appendMessage("agent", "⚠ Error connecting to Sentinel backend. Is the server running?");
  }

  state.isLoading = false;
}

function appendMessage(role, content) {
  const container = document.getElementById("chat-messages");
  const id = `msg-${Date.now()}`;
  const label = role === "user" ? "YOU" : "SENTINEL";
  container.innerHTML += `
    <div class="msg msg-${role}" id="${id}">
      <div class="msg-label">${label}</div>
      <div class="msg-bubble">${escapeHtml(content)}</div>
    </div>
  `;
  container.scrollTop = container.scrollHeight;
  return id;
}

function appendLoading() {
  const container = document.getElementById("chat-messages");
  const id = `loading-${Date.now()}`;
  container.innerHTML += `
    <div class="loading" id="${id}">
      <div class="spinner"></div>THINKING...
    </div>
  `;
  container.scrollTop = container.scrollHeight;
  return id;
}

async function runResearch() {
  const query = document.getElementById("research-query").value.trim();
  if (!query) return;

  const btn = document.getElementById("research-btn");
  const log = document.getElementById("research-log");
  const result = document.getElementById("research-result");

  btn.disabled = true;
  btn.textContent = "RESEARCHING...";
  log.style.display = "block";
  result.style.display = "none";

  const steps = [
    "[ PLANNER ] → GENERATING RESEARCH PLAN",
    "[ SEARCHER ] → QUERYING TAVILY AI",
    "[ SEARCHER ] → FETCHING SOURCES",
    "[ SYNTHESIZER ] → BUILDING REPORT",
  ];

  let stepIndex = 0;
  const logInterval = setInterval(() => {
    if (stepIndex < steps.length) log.textContent = steps[stepIndex++];
  }, 900);

  try {
    // Refresh page info before each request to get the current URL
    await loadPageInfo();
    const res = await chrome.runtime.sendMessage({
      type: "RUN_RESEARCH",
      payload: {
        url: state.pageInfo.url,
        page_content: state.pageInfo.content,
        query,
        session_id: state.sessionId,
      },
    });

    clearInterval(logInterval);
    log.style.display = "none";

    const data = res?.result;
    if (!data) throw new Error("No result");

    const sources = (data.sources || []).filter(Boolean).map(url =>
      `<a class="source-link" href="${url}" target="_blank">↗ ${url.slice(0, 48)}...</a>`
    ).join("<br>");

    result.style.display = "block";
    result.innerHTML = `
      <div class="research-result">${escapeHtml(data.synthesis || "No synthesis available.")}</div>
      ${sources ? `
        <div class="card" style="margin-top:0">
          <div class="card-title" style="font-size:14px">SOURCES</div>
          ${sources}
        </div>` : ""}
    `;
  } catch (e) {
    clearInterval(logInterval);
    log.style.display = "none";
    result.style.display = "block";
    result.innerHTML = `<div class="research-result" style="border-left-color:#cc0000;color:#cc0000">⚠ RESEARCH FAILED — CHECK BACKEND</div>`;
  }

  btn.disabled = false;
  btn.textContent = "RUN RESEARCH →";
}

async function runSync() {
  const btn = document.getElementById("sync-btn");
  const resultEl = document.getElementById("sync-result");

  btn.disabled = true;
  btn.textContent = "SYNCING...";
  resultEl.style.display = "none";
// Refresh page info before each request to get the current URL
    await loadPageInfo();
    
  try {
    const res = await chrome.runtime.sendMessage({
      type: "RUN_SYNC",
      payload: {
        url: state.pageInfo.url,
        page_content: state.pageInfo.content,
        page_title: state.pageInfo.title,
        session_id: state.sessionId,
      },
    });

    const data = res?.result;
    resultEl.style.display = "block";

    if (data?.status === "already_synced") {
      resultEl.innerHTML = `
        <div class="card" style="border-left:5px solid #f59e0b;box-shadow:4px 4px 0 var(--black)">
          <div style="font-family:var(--font-mono);font-size:11px;font-weight:700;letter-spacing:0.08em;color:#b45309;margin-bottom:6px">⚠ ALREADY SYNCED</div>
          <div style="color:#666;font-size:12px;font-family:var(--font-mono)">This page exists in your Notion database.</div>
        </div>
      `;
    } else if (data?.status === "synced") {
      const tags = (data.tags || []).map(t => `<span class="tag">${t}</span>`).join("");
      const insights = (data.insights || []).map(i => `<div class="insight-item">${escapeHtml(i)}</div>`).join("");
      resultEl.innerHTML = `
        <div class="card" style="border-left:5px solid #000;box-shadow:4px 4px 0 var(--black)">
          <div style="font-family:var(--font-mono);font-size:11px;font-weight:700;letter-spacing:0.08em;margin-bottom:10px">✓ SYNCED TO NOTION</div>
          <div class="section-label" style="margin-bottom:8px">SUMMARY</div>
          <p style="font-size:12px;line-height:1.55;margin-bottom:12px">${escapeHtml(data.summary || "")}</p>
          ${tags ? `<div class="section-label" style="margin-bottom:8px">TAGS</div><div class="tags-row" style="margin-bottom:12px">${tags}</div>` : ""}
          ${insights ? `<div class="section-label" style="margin-bottom:8px">INSIGHTS</div><div style="display:flex;flex-direction:column;gap:5px">${insights}</div>` : ""}
        </div>
      `;
    }
  } catch (e) {
    resultEl.style.display = "block";
    resultEl.innerHTML = `<div class="card" style="color:#cc0000;font-family:var(--font-mono);font-size:11px">⚠ SYNC FAILED — CHECK BACKEND + NOTION CREDENTIALS</div>`;
  }

  btn.disabled = false;
  btn.textContent = "SYNC TO NOTION →";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function removeElement(id) {
  document.getElementById(id)?.remove();
}

init();