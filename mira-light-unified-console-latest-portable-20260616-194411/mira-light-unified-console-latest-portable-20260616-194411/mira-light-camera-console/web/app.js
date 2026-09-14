const connectionStatus = document.getElementById("connection-status");
const latestTime = document.getElementById("latest-time");
const frameMeta = document.getElementById("frame-meta");
const latestImage = document.getElementById("latest-image");
const placeholder = document.getElementById("placeholder");
const configList = document.getElementById("config-list");
const errorView = document.getElementById("error-view");
const intervalInput = document.getElementById("interval-input");
const startButton = document.getElementById("start-watch");
const stopButton = document.getElementById("stop-watch");
const captureButton = document.getElementById("capture-once");

let busy = false;
let lastImageUrl = "";

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function text(value) {
  if (value === undefined || value === null || value === "") return "-";
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}

function escapeHtml(value) {
  return text(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

function renderConfig(config = {}) {
  const rows = [
    ["Host", `${config.boardUser || "-"}@${config.boardHost || "-"}:${config.boardPort || "-"}`],
    ["Password", config.passwordConfigured ? "configured" : "empty"],
    ["Device", config.remoteDevice],
    ["Format", `${config.inputFormat || "-"} · ${config.videoSize || "-"}`],
    ["Saved", config.captureDir],
  ];
  configList.innerHTML = rows.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
}

function renderState(state) {
  const latest = state.latestFrame;
  intervalInput.value = Math.round(Number(state.intervalSeconds || 10));
  startButton.disabled = state.running || busy;
  stopButton.disabled = !state.running || busy;
  captureButton.disabled = state.captureInProgress || busy;
  connectionStatus.textContent = state.captureInProgress ? "抓图中" : state.running ? "自动刷新中" : "已暂停";
  connectionStatus.dataset.status = state.lastError ? "bad" : state.captureInProgress ? "warn" : state.running ? "ok" : "idle";

  if (latest) {
    latestTime.textContent = latest.capturedAt || "-";
    frameMeta.textContent = `${Math.round((latest.sizeBytes || 0) / 1024)} KB · ${latest.durationSeconds || "-"}s`;
    if (latest.imageUrl && latest.imageUrl !== lastImageUrl) {
      lastImageUrl = latest.imageUrl;
      latestImage.src = latest.imageUrl;
    }
    latestImage.classList.add("visible");
    placeholder.classList.add("hidden");
  } else {
    latestTime.textContent = "-";
    frameMeta.textContent = "-";
    latestImage.classList.remove("visible");
    placeholder.classList.remove("hidden");
  }

  renderConfig(state.config || {});
  errorView.textContent = state.lastError ? `${state.lastError.at}\n${state.lastError.message}` : "-";
}

async function refreshState() {
  try {
    const state = await fetchJson("/api/frame/latest");
    renderState(state);
  } catch (error) {
    connectionStatus.textContent = "服务异常";
    connectionStatus.dataset.status = "bad";
    errorView.textContent = error.message || String(error);
  }
}

async function runAction(fn) {
  if (busy) return;
  busy = true;
  try {
    const state = await fn();
    renderState(state.state || state);
  } catch (error) {
    errorView.textContent = error.message || String(error);
    await refreshState();
  } finally {
    busy = false;
    await refreshState();
  }
}

startButton.addEventListener("click", () => {
  const intervalSeconds = Number(intervalInput.value || 10);
  runAction(() => fetchJson("/api/watch/start", { method: "POST", body: JSON.stringify({ intervalSeconds }) }));
});

stopButton.addEventListener("click", () => {
  runAction(() => fetchJson("/api/watch/stop", { method: "POST", body: "{}" }));
});

captureButton.addEventListener("click", () => {
  runAction(() => fetchJson("/api/capture", { method: "POST", body: "{}" }));
});

refreshState();
setInterval(refreshState, 1000);
