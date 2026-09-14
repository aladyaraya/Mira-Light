const statusBand = document.getElementById("status-band");
const runtimeList = document.getElementById("runtime-list");
const latestJob = document.getElementById("latest-job");
const jobsBody = document.getElementById("jobs-body");
const logsView = document.getElementById("logs");
const jobCount = document.getElementById("job-count");
const logCount = document.getElementById("log-count");
const lastUpdated = document.getElementById("last-updated");
const focusTriggerButton = document.getElementById("toggle-focus-trigger");

let busy = false;
let chromeTriggerMode = "launch_or_focus";

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function stringify(value) {
  if (value === undefined || value === null || value === "") return "-";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.join(", ") || "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function escapeHtml(value) {
  return stringify(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

function statusClass(item) {
  if (item?.ok === true || item?.running === true) return "ok";
  if (item?.ok === false || item?.running === false) return "bad";
  return "warn";
}

function renderStatus(health) {
  const checks = health.checks || {};
  const items = [
    ["Camera", checks.camera, checks.camera?.requested || "-"],
    ["Seedream API", checks.api, checks.api?.ok ? "ARK_API_KEY" : "Missing ARK_API_KEY"],
    ["Printer Bridge", checks.printerBridge, checks.printerBridge?.url || "-"],
    ["CUPS", checks.cups, checks.cups?.default || "-"],
    ["Watcher", checks.watcher, checks.watcher?.running ? `pid ${checks.watcher.pid}` : "stopped"],
    ["Worker", checks.worker, checks.worker?.running ? `pid ${checks.worker.pid}` : "stopped"],
    ["Chrome Trigger", checks.chromeTriggerMode, checks.chromeTriggerMode?.launchOrFocus ? "launch + focus" : "launch only"],
    ["Swift", checks.swift, checks.swift?.path || "-"],
    ["imagesnap", checks.imagesnap, checks.imagesnap?.path || "-"],
  ];
  statusBand.innerHTML = items
    .map(([label, item, value]) => {
      const cls = statusClass(item);
      return `
        <div class="status-item ${cls}">
          <div class="status-label">${escapeHtml(label)}</div>
          <div class="status-value"><span>${escapeHtml(value)}</span><i class="dot"></i></div>
        </div>
      `;
    })
    .join("");
}

function renderRuntime(status) {
  const config = status.config || {};
  chromeTriggerMode = config.chromeTriggerMode || "launch_or_focus";
  renderFocusTriggerButton();
  const rows = [
    ["Camera", `${config.cameraName || "-"} (${config.cameraBackend || "-"})`],
    ["Chrome Trigger", config.chromeLaunchOrFocus ? "launch + focus" : "launch only"],
    ["Auto Print", config.autoPrint],
    ["Print Media", config.printMedia],
    ["Printer URL", config.printerUrl],
    ["API Key", config.apiKeyPresent ? "present" : "missing"],
    ["Runtime", config.runtimeDir],
    ["Data", config.dataDir],
    ["Output", config.outputDir],
    ["Logs", config.logsDir],
  ];
  runtimeList.innerHTML = rows.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
  latestJob.textContent = JSON.stringify(status.latestJob || {}, null, 2);
}

function renderFocusTriggerButton() {
  const enabled = chromeTriggerMode === "launch_or_focus";
  focusTriggerButton.textContent = enabled ? "切回 Chrome 触发：开" : "切回 Chrome 触发：关";
  focusTriggerButton.classList.toggle("active", enabled);
  focusTriggerButton.title = enabled
    ? "Chrome 启动或从别的应用切回 Chrome 时都会触发新任务"
    : "只在 Chrome 从未运行到启动时触发新任务";
}

function renderJobs(payload) {
  const items = payload.items || [];
  jobCount.textContent = String(items.length);
  jobsBody.innerHTML = items
    .slice(0, 30)
    .map((job) => `
      <tr>
        <td>${escapeHtml(job.job_id)}</td>
        <td>${escapeHtml(job.status)}</td>
        <td>${escapeHtml(job.trigger)}</td>
        <td>${escapeHtml(job.output_path || job.portrait_path)}</td>
        <td>${escapeHtml(job.updated_at || job.created_at)}</td>
      </tr>
    `)
    .join("");
}

function renderLogs(payload) {
  const blocks = payload.items || [];
  logCount.textContent = String(blocks.length);
  logsView.textContent = blocks
    .map((block) => [`== ${block.name} ==`, ...(block.lines || [])].join("\n"))
    .join("\n\n");
}

async function refreshAll() {
  try {
    const [health, status, jobs, logs] = await Promise.all([
      fetchJson("/api/health"),
      fetchJson("/api/status"),
      fetchJson("/api/jobs"),
      fetchJson("/api/logs"),
    ]);
    renderStatus(health);
    renderRuntime(status);
    renderJobs(jobs);
    renderLogs(logs);
    lastUpdated.textContent = new Date().toLocaleTimeString();
  } catch (error) {
    logsView.textContent = `[ui-error] ${error.message}`;
  }
}

async function action(fn) {
  if (busy) return;
  busy = true;
  try {
    await fn();
  } catch (error) {
    logsView.textContent = `[action-error] ${error.message}\n\n${logsView.textContent}`;
  } finally {
    busy = false;
    await refreshAll();
  }
}

document.getElementById("refresh").addEventListener("click", refreshAll);
document.getElementById("start-watch").addEventListener("click", () => action(() => fetchJson("/api/watch/start", { method: "POST", body: "{}" })));
document.getElementById("stop-watch").addEventListener("click", () => action(() => fetchJson("/api/watch/stop", { method: "POST", body: "{}" })));
focusTriggerButton.addEventListener("click", () => {
  const nextMode = chromeTriggerMode === "launch_or_focus" ? "launch" : "launch_or_focus";
  action(() => fetchJson("/api/watch/mode", { method: "POST", body: JSON.stringify({ mode: nextMode }) }));
});
document.getElementById("capture-render").addEventListener("click", () => action(() => fetchJson("/api/capture-render", { method: "POST", body: "{}" })));
document.getElementById("print-last").addEventListener("click", () => action(() => fetchJson("/api/print-last", { method: "POST", body: "{}" })));

refreshAll();
setInterval(refreshAll, 5000);
