const sceneGrid = document.getElementById("scene-grid");
const quickGrid = document.getElementById("quick-grid");
const lightShowcaseGrid = document.getElementById("light-showcase-grid");
const lightShowcaseRefreshButton = document.getElementById("light-showcase-refresh");
const queueList = document.getElementById("queue-list");
const queueSummary = document.getElementById("queue-summary");
const output = document.getElementById("output");
const outputTitle = document.getElementById("output-title");
const boardSummary = document.getElementById("board-summary");
const passwordSummary = document.getElementById("password-summary");
const running = document.getElementById("running");
const current = document.getElementById("current");
const lastCode = document.getElementById("last-code");
const servoPositionSummary = document.getElementById("servo-position-summary");
const refreshServosButton = document.getElementById("refresh-servos");
const servoIds = ["0", "1", "2", "3"];
const servoPositionEls = servoIds.map((id) => document.getElementById(`servo-pos-${id}`));
const servoTargetEls = servoIds.map((id) => document.getElementById(`servo-target-${id}`));
const servoStepInput = document.getElementById("servo-step");
const servoControlButtons = Array.from(document.querySelectorAll("[data-servo-delta]"));
const hostInput = document.getElementById("host");
const portInput = document.getElementById("port");
const userInput = document.getElementById("user");
const passwordInput = document.getElementById("password");
const connectionCheckButton = document.getElementById("connection-check");
const connectionStatus = document.getElementById("connection-status");
const cameraFrame = document.querySelector(".camera-frame");
const cameraImage = document.getElementById("camera-image");
const cameraState = document.getElementById("camera-state");
const cameraUpdated = document.getElementById("camera-updated");
const cameraMeta = document.getElementById("camera-meta");
const cameraStartButton = document.getElementById("camera-start");
const cameraStopButton = document.getElementById("camera-stop");
const cameraCaptureButton = document.getElementById("camera-capture");
const cameraRenderPrintLatestButton = document.getElementById("camera-render-print-latest");
const cameraReprintLatestRenderButton = document.getElementById("camera-reprint-latest-render");
const printStepTask = document.getElementById("print-step-task");
const printStepRender = document.getElementById("print-step-render");
const printStepSubmit = document.getElementById("print-step-submit");
const printStepPrinter = document.getElementById("print-step-printer");
const printerHealthState = document.getElementById("printer-health-state");
const printerHealthDetail = document.getElementById("printer-health-detail");
const reprintProcessSummary = document.getElementById("reprint-process-summary");
const reprintProcessList = document.getElementById("reprint-process-list");
const bookFollowState = document.getElementById("book-follow-state");
const bookFollowDetector = document.getElementById("book-follow-detector");
const bookFollowTarget = document.getElementById("book-follow-target");
const bookFollowBridge = document.getElementById("book-follow-bridge");
const bookFollowUpdate = document.getElementById("book-follow-update");
const bookFollowBaseUrl = document.getElementById("book-follow-base-url");
const bookFollowPort = document.getElementById("book-follow-port");
const bookFollowSaturation = document.getElementById("book-follow-saturation");
const bookFollowColorRatio = document.getElementById("book-follow-color-ratio");
const bookFollowUpdateMs = document.getElementById("book-follow-update-ms");
const bookFollowStartButton = document.getElementById("book-follow-start");
const bookFollowStopButton = document.getElementById("book-follow-stop");
const bookFollowRefreshButton = document.getElementById("book-follow-refresh");
const bookFollowLog = document.getElementById("book-follow-log");
const touchActive = document.getElementById("touch-active");
const touchEnabled = document.getElementById("touch-enabled");
const touchSensitivity = document.getElementById("touch-sensitivity");
const touchFirmware = document.getElementById("touch-firmware");
const touchMappingVersion = document.getElementById("touch-mapping-version");
const touchHysteresis = document.getElementById("touch-hysteresis");
const touchReleaseDebounce = document.getElementById("touch-release-debounce");
const touchAudioState = document.getElementById("touch-audio-state");
const touchAudioBridge = document.getElementById("touch-audio-bridge");
const touchUpdated = document.getElementById("touch-updated");
const touchLog = document.getElementById("touch-log");
const touchStartButton = document.getElementById("touch-start");
const touchStopButton = document.getElementById("touch-stop");
const touchDisableButton = document.getElementById("touch-disable");
const touchEnableButton = document.getElementById("touch-enable");
const touchAudioCheckButton = document.getElementById("touch-audio-check");
const narrationPlayButton = document.getElementById("narration-play");
const touchSensitivityButtons = Array.from(document.querySelectorAll("[data-touch-preset]"));
const teachMotionState = document.getElementById("teach-motion-state");
const teachStartButton = document.getElementById("teach-start");
const teachStopButton = document.getElementById("teach-stop");
const teachPlayButton = document.getElementById("teach-play");
const showState = document.getElementById("show-state");
const showActiveStep = document.getElementById("show-active-step");
const showBook = document.getElementById("show-book");
const showPhoto = document.getElementById("show-photo");
const showLocks = document.getElementById("show-locks");
const showFeedback = document.getElementById("show-feedback");
const showStepButtons = Array.from(document.querySelectorAll("[data-show-step]"));
const showResetButton = document.getElementById("show-reset");
const voiceMotionDemoButtons = Array.from(document.querySelectorAll("[data-voice-motion-demo]"));
const openCelebrationPageButton = document.getElementById("open-celebration-page");
const celebrationPageUrl = `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8777/08_celebrate/index.html`;
const LIGHT_SHOWCASE_IDS = [
  "led_warm",
  "led_white",
  "led_white_spin",
  "led_rainbow_spin",
  "led_blue_spin",
  "led_off",
];

let registry = null;
let lastRenderedResultKey = null;
let latestState = null;
let connectionCheckInFlight = false;
let servoRefreshInFlight = false;
let servoControlInFlight = false;
let servoControlPending = false;
let cameraRefreshInFlight = false;
let printerHealthRefreshInFlight = false;
let reprintJobsRefreshInFlight = false;
let bookFollowRefreshInFlight = false;
let touchRefreshInFlight = false;
let teachRefreshInFlight = false;
let latestTouchStatus = null;
let touchAudioCheckInFlight = false;
let showRefreshInFlight = false;
let servoHoldTimer = null;
const servoTargets = Object.fromEntries(servoIds.map((id) => [id, null]));
const servoMin = 0;
const servoMax = 4095;

function connectionPayload() {
  return {
    host: hostInput.value.trim(),
    port: Number(portInput.value || 22),
    user: userInput.value.trim(),
    password: passwordInput.value,
  };
}

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

function renderConnectionDiagnosis(payload = {}) {
  const diagnosis = payload.diagnosis || payload;
  const tcpOk = diagnosis.tcp?.ok;
  const sshOk = diagnosis.ssh?.ok;
  if (tcpOk && sshOk) {
    connectionStatus.textContent = `SSH 直连正常 · ${diagnosis.updatedAt || "-"}`;
    return;
  }
  const detail =
    (diagnosis.warnings && diagnosis.warnings[0]) ||
    diagnosis.ssh?.stderr ||
    diagnosis.tcp?.error ||
    "SSH 未连通";
  connectionStatus.textContent = `SSH 异常 · ${detail}`;
}

function riskLabel(risk) {
  const labels = {
    "light-only": "只动灯",
    "read-only": "只读",
    "motion-medium": "中风险机械",
    "motion-high": "高风险机械",
    "motion-emergency": "高优先级救场",
    "system-recovery": "系统恢复",
  };
  return labels[risk] || risk;
}

function showOutput(title, payload) {
  outputTitle.textContent = title;
  output.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function cleanRemoteOutput(text) {
  return String(text || "")
    .replace(/\r/g, "")
    .split("\n")
    .filter((line) => {
      const trimmed = line.trim();
      return trimmed && !trimmed.startsWith("spawn ssh ") && !trimmed.includes("'s password:");
    })
    .join("\n")
    .trim();
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) {
    return "-";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function setProgressStep(element, text, state = "idle") {
  if (!element) {
    return;
  }
  element.textContent = text;
  element.dataset.state = state;
}

function renderPrintProgress(photo = {}) {
  const job = (photo.renderJobs || [])[0] || null;
  if (!job) {
    setProgressStep(printStepTask, "等待", "idle");
    setProgressStep(printStepRender, "等待", "idle");
    setProgressStep(printStepSubmit, "等待", "idle");
    setProgressStep(printStepPrinter, "等待", "idle");
    return;
  }

  const failed = job.status === "failed";
  const done = job.status === "done";
  setProgressStep(
    printStepTask,
    failed ? "失败" : done ? "完成" : job.status === "running" ? "进行中" : "已创建",
    failed ? "failed" : done ? "done" : "running",
  );
  setProgressStep(
    printStepRender,
    job.renderOutput ? "已渲染" : failed ? "未完成" : "渲染中",
    job.renderOutput ? "done" : failed ? "failed" : "running",
  );
  setProgressStep(printStepSubmit, job.createdAt ? "已提交任务" : "等待", job.createdAt ? "done" : "idle");
  if (job.printResult?.job_id || job.printResult?.jobId) {
    setProgressStep(printStepPrinter, `已发送 ${job.printResult.job_id || job.printResult.jobId}`, "done");
  } else if (failed) {
    setProgressStep(printStepPrinter, job.error || "发送失败", "failed");
  } else if (job.renderOutput) {
    setProgressStep(printStepPrinter, "发送中", "running");
  } else {
    setProgressStep(printStepPrinter, "等待渲染", "idle");
  }
}

function renderPrinterHealth(payload = {}) {
  const printer = payload.printer || {};
  const bridge = payload.bridge || {};
  printerHealthState.textContent = payload.ok ? "健康" : "异常";
  printerHealthState.dataset.state = payload.ok ? "done" : "failed";
  printerHealthDetail.textContent = [
    payload.bridgeUrl || "-",
    payload.tokenConfigured ? "token ok" : "token missing",
    printer.queue_name || printer.queueName || bridge.queue_name || "",
    printer.error || bridge.error || "",
  ]
    .filter(Boolean)
    .join(" · ");
}

function reprintStage(job = {}) {
  if (job.status === "failed") {
    return job.error || "失败";
  }
  if (job.printResult?.job_id || job.printResult?.jobId) {
    return "已发送给打印机";
  }
  if (job.stage === "submitting" || job.status === "running") {
    return "提交打印中";
  }
  if (job.status === "done") {
    return "完成";
  }
  return "已创建";
}

function renderReprintJobs(payload = {}) {
  if (!reprintProcessList || !reprintProcessSummary) {
    return;
  }
  const jobs = payload.reprintJobs || [];
  reprintProcessSummary.textContent = jobs.length ? `${jobs.length} 个任务` : "等待任务。";
  if (!jobs.length) {
    reprintProcessList.innerHTML = '<div class="reprint-process-empty">暂无重打任务。</div>';
    return;
  }
  reprintProcessList.innerHTML = "";
  for (const job of jobs.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "reprint-process-row";
    row.dataset.state = job.status || "pending";
    const printId = job.printResult?.job_id || job.printResult?.jobId || job.error || "-";
    const timeCell = document.createElement("span");
    timeCell.textContent = job.updatedAt || job.createdAt || "-";
    const stageCell = document.createElement("strong");
    stageCell.textContent = reprintStage(job);
    const printCell = document.createElement("code");
    printCell.textContent = printId;
    row.append(timeCell, stageCell, printCell);
    reprintProcessList.appendChild(row);
  }
}

async function refreshReprintJobs() {
  if (reprintJobsRefreshInFlight) {
    return;
  }
  reprintJobsRefreshInFlight = true;
  try {
    const data = await fetchJson("/api/camera/reprint-jobs");
    renderReprintJobs(data);
  } catch (error) {
    renderReprintJobs({ reprintJobs: [{ status: "failed", error: error.message || String(error), updatedAt: "读取失败" }] });
  } finally {
    reprintJobsRefreshInFlight = false;
  }
}

async function refreshPrinterHealth() {
  if (printerHealthRefreshInFlight) {
    return;
  }
  printerHealthRefreshInFlight = true;
  try {
    const response = await fetch("/api/printer/health");
    const data = await response.json();
    renderPrinterHealth(data);
  } catch (error) {
    renderPrinterHealth({ ok: false, error: error.message || String(error), printer: { error: error.message || String(error) } });
  } finally {
    printerHealthRefreshInFlight = false;
  }
}

function renderCamera(state = {}) {
  const latestFrame = state.latestFrame;
  const runningText = state.running ? "自动刷新中" : "已暂停";
  const captureText = state.captureInProgress ? " · 抓取中" : "";
  const errorText = state.lastError ? ` · ${state.lastError.message}` : "";
  cameraState.textContent = `${runningText}${captureText}${errorText}`;

  if (latestFrame?.imageUrl) {
    cameraImage.src = latestFrame.imageUrl;
    cameraFrame.classList.add("has-image");
    cameraUpdated.textContent = latestFrame.capturedAt ? `更新于 ${latestFrame.capturedAt}` : "已有画面";
    cameraMeta.textContent = `${formatBytes(latestFrame.sizeBytes)} · ${latestFrame.durationSeconds ?? "-"}s`;
  } else {
    cameraFrame.classList.remove("has-image");
    cameraUpdated.textContent = state.lastError ? `错误于 ${state.lastError.at || "-"}` : "尚未抓取";
    cameraMeta.textContent = state.config?.videoSize || "-";
  }

  cameraStartButton.disabled = Boolean(state.running);
  cameraStopButton.disabled = !state.running;
  cameraCaptureButton.disabled = Boolean(state.captureInProgress);
}

async function refreshCamera() {
  if (cameraRefreshInFlight) {
    return;
  }
  cameraRefreshInFlight = true;
  try {
    const data = await fetchJson("/api/camera/latest");
    renderCamera(data);
  } catch (error) {
    cameraState.textContent = `摄像头状态失败：${error.message || String(error)}`;
  } finally {
    cameraRefreshInFlight = false;
  }
}

async function cameraAction(path, title) {
  const data = await fetchJson(path, { method: "POST", body: JSON.stringify({ intervalSeconds: 2 }) });
  renderCamera(data.state || data);
  showOutput(title, data.frame ? data.frame : data);
}

async function cameraRenderPrintLatestAction() {
  const data = await fetchJson("/api/camera/render-print-latest", {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderShow(data.status || data);
  await refreshPrinterHealth().catch(() => {});
  showOutput("摄像头 · 当前画面已提交渲染打印", data);
}

async function cameraReprintLatestRenderAction() {
  const data = await fetchJson("/api/camera/reprint-latest-render", {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderShow(data.status || data);
  renderReprintJobs((data.status || data).photo || {});
  await refreshReprintJobs().catch(() => {});
  await refreshPrinterHealth().catch(() => {});
  showOutput("摄像头 · 最新渲染图已重新提交打印", data);
}

async function checkConnection({ quiet = false } = {}) {
  if (connectionCheckInFlight) {
    return;
  }
  connectionCheckInFlight = true;
  connectionStatus.textContent = "SSH 检查中...";
  connectionCheckButton.disabled = true;
  try {
    const data = await fetchJson("/api/connection-diagnose", {
      method: "POST",
      body: JSON.stringify(connectionPayload()),
    });
    renderConnectionDiagnosis(data);
    if (!quiet) {
      showOutput("SSH 自检", data);
    }
  } catch (error) {
    connectionStatus.textContent = `SSH 异常 · ${error.message || String(error)}`;
    if (!quiet) {
      throw error;
    }
  } finally {
    connectionCheckInFlight = false;
    connectionCheckButton.disabled = false;
  }
}

function setInputValue(input, value) {
  if (!input || document.activeElement === input || value === undefined || value === null) {
    return;
  }
  input.value = String(value);
}

function bookFollowPayload() {
  return {
    baseUrl: bookFollowBaseUrl.value.trim(),
    receiverPort: Number(bookFollowPort.value || 18000),
    minSaturation: Number(bookFollowSaturation.value || 70),
    minColorRatio: bookFollowColorRatio.value.trim() || "0.22",
    tabletopTrackingUpdateMs: Number(bookFollowUpdateMs.value || 160),
  };
}

function renderBookFollow(payload = {}) {
  const status = payload.status || payload;
  const config = status.config || {};
  const summary = status.summary || {};
  const forward = status.lastForward || {};
  const runningText = status.running ? "运行中" : "已停止";
  const detector = summary.detector || "-";
  const targetParts = [summary.targetClass, summary.targetSubclass].filter((item) => item && item !== "-");
  const bridgeParts = [summary.bridgeAction, summary.bridgeReason].filter(Boolean);

  bookFollowState.textContent = `${runningText} · ${status.receiverUrl || "等待接收端"}`;
  bookFollowDetector.textContent = detector;
  bookFollowTarget.textContent = targetParts.length ? targetParts.join(" / ") : "-";
  bookFollowBridge.textContent = bridgeParts.length ? bridgeParts.join(" · ") : "-";
  bookFollowUpdate.textContent = summary.recommendedUpdateMs ? `${summary.recommendedUpdateMs}ms` : "-";
  bookFollowStartButton.disabled = Boolean(status.running);
  bookFollowStopButton.disabled = !status.running;

  setInputValue(bookFollowBaseUrl, config.baseUrl);
  setInputValue(bookFollowPort, config.receiverPort);
  setInputValue(bookFollowSaturation, config.minSaturation);
  setInputValue(bookFollowColorRatio, config.minColorRatio);
  setInputValue(bookFollowUpdateMs, config.tabletopTrackingUpdateMs);

  const sections = [
    `SUMMARY\nrunning: ${status.running ? "yes" : "no"}\ndetector: ${detector}\ntarget: ${bookFollowTarget.textContent}\nbridge: ${bookFollowBridge.textContent}`,
    status.lastForward ? `FORWARD\nok: ${forward.ok ? "yes" : "no"}\nfile: ${forward.filename || "-"}\nurl: ${forward.url || "-"}\nstatus: ${forward.status ?? "-"}\nreason: ${forward.reason || forward.error || "-"}\nupdated: ${forward.updatedAt || "-"}` : "",
    config ? `CONFIG\nHSV: H=${config.hueMin}-${config.hueMax}, S>=${config.minSaturation}, V>=${config.minValue}\nROI_TOP: ${config.roiTop}\nMAX_AREA_RATIO: ${config.maxAreaRatio}\nBOOK_MIN_COLOR_RATIO: ${config.minColorRatio}\nTABLETOP_UPDATE_MS: ${config.tabletopTrackingUpdateMs}` : "",
    status.paths ? `FILES\nlatest: ${status.paths.latestEvent || "-"}\nbridge: ${status.paths.bridgeState || "-"}\nlog: ${status.paths.log || "-"}` : "",
    status.logTail ? `LOG\n${status.logTail}` : "",
  ].filter(Boolean);
  bookFollowLog.textContent = sections.join("\n\n") || "-";
}

function renderTeachMotion(teach = {}) {
  const busy = Boolean(teach.running) || teach.status === "playing" || teach.status === "starting";
  const runningText = teach.running ? "录制中 · 请手扶灯臂" : teach.status === "playing" ? "回放中" : teach.rawExists ? "已有录制" : "未录制 · 录制时请手扶灯臂";
  const details = [];
  if (teach.frameCount !== undefined && teach.frameCount !== null) {
    details.push(`${teach.frameCount} 帧`);
  }
  if (teach.durationMs !== undefined && teach.durationMs !== null) {
    details.push(`${(Number(teach.durationMs) / 1000).toFixed(1)}s`);
  }
  if (teach.error) {
    details.push(teach.error);
  }
  teachMotionState.textContent = [runningText, ...details].filter(Boolean).join(" · ");
  teachStartButton.disabled = busy || Boolean(latestState?.running);
  teachStopButton.disabled = !teach.running;
  teachPlayButton.disabled = busy || !teach.rawExists || Boolean(latestState?.running);
}

async function refreshTeachMotion() {
  if (teachRefreshInFlight) {
    return;
  }
  teachRefreshInFlight = true;
  try {
    const data = await fetchJson("/api/teach/status");
    renderTeachMotion(data.teachMotion || {});
  } catch (error) {
    teachMotionState.textContent = `示教状态失败：${error.message || String(error)}`;
  } finally {
    teachRefreshInFlight = false;
  }
}

async function teachMotionAction(action, title) {
  const data = await fetchJson(`/api/teach/${action}`, {
    method: "POST",
    body: JSON.stringify(connectionPayload()),
  });
  renderTeachMotion(data.teachMotion || {});
  const result = data.result ? formatExecutionResult(data.result) : data;
  showOutput(title, result);
  await refreshState();
}

async function refreshBookFollow() {
  if (bookFollowRefreshInFlight) {
    return;
  }
  bookFollowRefreshInFlight = true;
  try {
    const data = await fetchJson("/api/book-follow/status");
    renderBookFollow(data);
  } catch (error) {
    bookFollowState.textContent = `追书状态失败：${error.message || String(error)}`;
  } finally {
    bookFollowRefreshInFlight = false;
  }
}

async function bookFollowAction(path, title) {
  const data = await fetchJson(path, {
    method: "POST",
    body: JSON.stringify(bookFollowPayload()),
  });
  renderBookFollow(data.status || data);
  showOutput(title, data);
}

function renderShow(payload = {}) {
  const locks = payload.locks || {};
  const book = payload.book || {};
  const photo = payload.photo || {};
  const lockPairs = Object.entries(locks).map(([resource, owner]) => `${resource}:${owner}`);
  showState.textContent = `${payload.status || "idle"}${payload.lastError ? ` · ${payload.lastError}` : ""}`;
  showActiveStep.textContent = payload.activeStep || "-";
  showBook.textContent = book.locked ? `${book.title || "Big meets Little"} · locked` : book.title || "-";
  showPhoto.textContent = photo.lastSnapshot ? `${photo.lastMode || "photo"} · ${photo.lastSnapshot.split("/").pop()}` : "-";
  showLocks.textContent = lockPairs.length ? lockPairs.join(" / ") : "free";
  renderPrintProgress(photo);
  showFeedback.textContent = JSON.stringify(
    {
      status: payload.status,
      activeStep: payload.activeStep,
      locks,
      book: {
        locked: book.locked,
        title: book.title,
        detector: book.detector,
      },
      photo,
    },
    null,
    2,
  );
}

async function refreshShow() {
  if (showRefreshInFlight) {
    return;
  }
  showRefreshInFlight = true;
  try {
    const data = await fetchJson("/api/show/status");
    renderShow(data);
  } catch (error) {
    showState.textContent = `展示状态失败：${error.message || String(error)}`;
  } finally {
    showRefreshInFlight = false;
  }
}

function showStepPayload(step) {
  return {
    ...connectionPayload(),
    ...bookFollowPayload(),
    step,
  };
}

async function showStepAction(step) {
  const data = await fetchJson("/api/show/step", {
    method: "POST",
    body: JSON.stringify(showStepPayload(step)),
  });
  renderShow(data.status || data);
  if (data.bookFollow) {
    renderBookFollow(data.bookFollow);
  }
  await refreshState().catch(() => {});
  await refreshBookFollow().catch(() => {});
  await refreshCamera().catch(() => {});
  showOutput(`展示流程 · ${step}`, data);
}

async function resetShow() {
  const data = await fetchJson("/api/show/reset", {
    method: "POST",
    body: JSON.stringify(connectionPayload()),
  });
  renderShow(data);
  showOutput("展示流程 · 已重置", data);
}

async function voiceMotionDemoAction(demo) {
  const data = await fetchJson("/api/voice-motion-demo", {
    method: "POST",
    body: JSON.stringify({
      ...connectionPayload(),
      demo,
      playAudio: demo === "answer",
    }),
  });
  renderShow(data.status || data);
  await refreshState().catch(() => {});
  showOutput(`独立动作调试 · ${demo}`, data);
}

async function openCelebrationPage() {
  const data = await fetchJson("/api/celebration-page/ensure");
  const url = data.url || celebrationPageUrl;
  window.open(url, "_blank", "noopener");
  showOutput("庆祝页 · 健康检查通过", data);
}

function serviceStateLabel(value) {
  const labels = {
    active: "运行中",
    inactive: "已关闭",
    failed: "错误",
    activating: "启动中",
    deactivating: "关闭中",
    enabled: "已开启",
    disabled: "已关闭",
    static: "静态",
    unknown: "未知",
  };
  return labels[value] || value || "未知";
}

function renderTouch(payload = {}) {
  const status = payload.status || payload;
  latestTouchStatus = status;
  const config = status.config || {};
  const presets = status.sensitivityPresets || {};
  const activePreset = status.sensitivityPreset || "custom";
  const activePresetLabel = presets[activePreset]?.label || config._ui_sensitivity_label || "自定义";
  touchActive.textContent = serviceStateLabel(status.active);
  touchEnabled.textContent = serviceStateLabel(status.enabled);
  touchUpdated.textContent = status.updatedAt ? `更新于 ${status.updatedAt}` : "状态未知";
  touchSensitivity.textContent = activePresetLabel;
  touchFirmware.textContent = status.firmware?.thresholdCommand || (config.lamp_thr === undefined ? "-" : `THR,${config.lamp_thr}`);
  touchMappingVersion.textContent = config.version === undefined ? "-" : `v${config.version}`;
  touchHysteresis.textContent = config.thr_hysteresis === undefined ? "-" : String(config.thr_hysteresis);
  touchReleaseDebounce.textContent =
    config.release_debounce_ms === undefined ? "-" : `${config.release_debounce_ms}ms`;

  for (const button of touchSensitivityButtons) {
    const active = button.dataset.touchPreset === activePreset;
    button.classList.toggle("active", active);
    button.disabled = false;
    button.title = presets[button.dataset.touchPreset]?.description || "";
  }

  const sections = [
    status.firmware
      ? `FIRMWARE\nmapping: ${status.firmware.mappingPath || "-"}\nversion: ${status.firmware.mappingVersion ?? "-"}\ncommand: ${status.firmware.thresholdCommand || "-"}`
      : "",
    Object.keys(config).length ? `CONFIG\n${JSON.stringify(config, null, 2)}` : "",
    status.process ? `PROCESS\n${status.process}` : "",
    status.statusSummary ? `STATUS\n${status.statusSummary}` : "",
    status.logTail ? `LOG\n${status.logTail}` : "",
    status.stderr ? `STDERR\n${cleanRemoteOutput(status.stderr)}` : "",
  ].filter(Boolean);
  touchLog.textContent = sections.join("\n\n") || "-";
}

async function refreshTouch() {
  if (touchRefreshInFlight) {
    return;
  }
  touchRefreshInFlight = true;
  try {
    const data = await fetchJson("/api/touch/status");
    renderTouch(data.status);
  } catch (error) {
    touchUpdated.textContent = `读取失败：${error.message || String(error)}`;
  } finally {
    touchRefreshInFlight = false;
  }
}

function formatTouchAction(data) {
  const result = data.result || {};
  const status = data.status || {};
  const stdout = cleanRemoteOutput(result.stdout);
  const stderr = cleanRemoteOutput(result.stderr);
  return [
    `action: ${data.action}`,
    `returnCode: ${result.returnCode}`,
    `active: ${status.active}`,
    `enabled: ${status.enabled}`,
    stdout ? `stdout\n${stdout}` : "",
    stderr ? `stderr\n${stderr}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
}

async function touchAction(action, title) {
  const data = await fetchJson(`/api/touch/${action}`, {
    method: "POST",
    body: JSON.stringify(connectionPayload()),
  });
  renderTouch(data.status);
  showOutput(title, formatTouchAction(data));
}

function formatTouchSensitivityAction(data) {
  const result = data.result || {};
  const status = data.status || {};
  const preset = data.preset || {};
  const stdout = cleanRemoteOutput(result.stdout);
  const stderr = cleanRemoteOutput(result.stderr);
  return [
    `preset: ${preset.label || preset.id || "-"}`,
    preset.description || "",
    `returnCode: ${result.returnCode}`,
    `active: ${status.active}`,
    `threshold: ${status.firmware?.thresholdCommand || "-"}`,
    stdout ? `stdout\n${stdout}` : "",
    stderr ? `stderr\n${stderr}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
}

async function touchSensitivityAction(presetId) {
  const current = latestTouchStatus || {};
  const presets = current.sensitivityPresets || {};
  const preset = presets[presetId] || { id: presetId, label: presetId, values: {} };
  const optimisticConfig = {
    ...(current.config || {}),
    ...(preset.values || {}),
    _ui_sensitivity_preset: presetId,
    _ui_sensitivity_label: preset.label || presetId,
  };
  renderTouch({
    ...current,
    config: optimisticConfig,
    sensitivityPreset: presetId,
    firmware: {
      ...(current.firmware || {}),
      thresholdCommand:
        optimisticConfig.lamp_thr === undefined ? current.firmware?.thresholdCommand : `THR,${optimisticConfig.lamp_thr}`,
    },
    updatedAt: "正在写入...",
  });
  for (const button of touchSensitivityButtons) {
    button.disabled = button.dataset.touchPreset !== presetId;
  }
  try {
    const data = await fetchJson("/api/touch/sensitivity", {
      method: "POST",
      body: JSON.stringify({ ...connectionPayload(), preset: presetId }),
    });
    renderTouch(data.status);
    showOutput("摸摸系统 · 灵敏度已更新", formatTouchSensitivityAction(data));
  } catch (error) {
    await refreshTouch().catch(() => {});
    throw error;
  } finally {
    for (const button of touchSensitivityButtons) {
      button.disabled = false;
    }
  }
}

function renderTouchAudio(status = {}) {
  const running = Boolean(status.running || status.local?.running);
  const repaired = status.repair?.started;
  touchAudioState.textContent = running ? (repaired ? "已拉起" : "正常") : "异常";
  touchAudioBridge.textContent = status.local?.port ? String(status.local.port) : "-";
}

function formatTouchAudioCheck(data) {
  const status = data.status || {};
  const local = status.local || {};
  const repair = status.repair || {};
  const board = status.board || {};
  const lines = [
    `running: ${status.running ? "yes" : "no"}`,
    `local: ${local.healthUrl || "-"}`,
    `repair: ${repair.reason || "-"}`,
    `board: ${board.ok === undefined ? "skipped" : board.ok ? "ok" : "failed"}`,
    board.probe?.bridge_url ? `bridge_url: ${board.probe.bridge_url}` : "",
    board.probe?.trigger ? `trigger: ${board.probe.trigger.ok ? "ok" : "failed"}` : "",
    board.stderr ? `stderr\n${cleanRemoteOutput(board.stderr)}` : "",
  ];
  return lines.filter(Boolean).join("\n");
}

async function checkTouchAudio({ quiet = false, boardCheck = false, testAudio = false } = {}) {
  if (touchAudioCheckInFlight) {
    return;
  }
  touchAudioCheckInFlight = true;
  try {
    const data = await fetchJson("/api/touch-audio/check", {
      method: "POST",
      body: JSON.stringify({
        ...connectionPayload(),
        autoStart: true,
        boardCheck,
        testAudio,
      }),
    });
    renderTouchAudio(data.status);
    if (!quiet) {
      showOutput("摸摸语音 · 自检完成", formatTouchAudioCheck(data));
    }
  } catch (error) {
    renderTouchAudio({ running: false, local: { port: "-" } });
    if (!quiet) {
      throw error;
    }
  } finally {
    touchAudioCheckInFlight = false;
  }
}

async function narrationAction() {
  const data = await fetchJson("/api/audio/narration", {
    method: "POST",
    body: JSON.stringify({}),
  });
  showOutput("念白 · 已播放", `pid: ${data.audio?.pid || "-"}\npath: ${data.audio?.path || "-"}`);
}

function parseServoPositions(stdout) {
  const positions = {};
  let currentId = null;
  for (const line of String(stdout || "").replace(/\r/g, "").split("\n")) {
    const idMatch = line.match(/^Read ID\s*:\s*(\d+)/);
    if (idMatch) {
      currentId = idMatch[1];
      continue;
    }
    const positionMatch = line.match(/^Position\s*:\s*(\d+)/);
    if (positionMatch && currentId !== null) {
      positions[currentId] = Number(positionMatch[1]);
      currentId = null;
    }
  }
  return positions;
}

function servoPositionLines(positions) {
  return servoIds
    .filter((id) => positions[id] !== undefined)
    .map((id) => `舵机 ${id}: ${positions[id]}`);
}

function clampServoPosition(value) {
  return Math.max(servoMin, Math.min(servoMax, Math.round(Number(value))));
}

function servoStepSize() {
  const value = Number(servoStepInput.value || 20);
  return Math.max(1, Math.min(200, Math.round(value)));
}

function hasCompleteServoTargets() {
  return servoIds.every((id) => Number.isFinite(servoTargets[id]));
}

function syncServoTargets(values, { force = false } = {}) {
  for (const id of servoIds) {
    if (values[id] !== undefined && (force || !Number.isFinite(servoTargets[id]))) {
      servoTargets[id] = clampServoPosition(values[id]);
    }
  }
  renderServoControls();
}

function renderServoControls() {
  for (let index = 0; index < servoTargetEls.length; index += 1) {
    const value = servoTargets[servoIds[index]];
    servoTargetEls[index].textContent = Number.isFinite(value) ? String(value) : "-";
  }

  const queueBusy = latestState && (latestState.running || (latestState.queue || []).length > 0);
  const externalControlBusy = latestState?.servoControl?.running && !servoControlInFlight;
  const disabled = queueBusy || externalControlBusy || !hasCompleteServoTargets();
  for (const button of servoControlButtons) {
    button.disabled = disabled;
  }
}

function manualServoErrorText(error) {
  if (!error) {
    return "";
  }
  if (String(error).includes("refresh")) {
    return "正在读取当前位置，稍后重试";
  }
  if (String(error).includes("queue")) {
    return "队列执行中，暂停微调";
  }
  return String(error);
}

async function sendServoTargets() {
  if (!hasCompleteServoTargets()) {
    servoPositionSummary.textContent = "请先刷新当前位置。";
    return;
  }
  if (servoControlInFlight) {
    servoControlPending = true;
    return;
  }

  servoControlInFlight = true;
  servoPositionSummary.textContent = "微调发送中...";
  try {
    const response = await fetch("/api/servo-control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...connectionPayload(),
        positions: Object.fromEntries(servoIds.map((id) => [id, servoTargets[id]])),
      }),
    });
    const data = await response.json();
    if (response.status === 409) {
      const message = data.error || "";
      servoPositionSummary.textContent = manualServoErrorText(message);
      if (message.includes("refresh") || message.includes("already running")) {
        servoControlPending = true;
      }
      return;
    }
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || data.servoPositions?.error || `HTTP ${response.status}`);
    }
    renderServoPositions(data.servoPositions);
    syncServoTargets(data.servoPositions.values || {}, { force: true });
    await refreshState();
  } catch (error) {
    servoPositionSummary.textContent = `微调失败：${error.message || String(error)}`;
  } finally {
    servoControlInFlight = false;
    if (servoControlPending) {
      servoControlPending = false;
      setTimeout(() => {
        sendServoTargets().catch(() => {});
      }, 120);
    }
  }
}

function nudgeServo(servoId, direction) {
  if (!Number.isFinite(servoTargets[servoId])) {
    servoPositionSummary.textContent = "请先刷新当前位置。";
    return;
  }
  servoTargets[servoId] = clampServoPosition(servoTargets[servoId] + direction * servoStepSize());
  renderServoControls();
  sendServoTargets().catch(() => {});
}

function stopServoHold() {
  if (servoHoldTimer !== null) {
    clearInterval(servoHoldTimer);
    servoHoldTimer = null;
  }
}

function startServoHold(button) {
  const row = button.closest("[data-servo-id]");
  if (!row || button.disabled) {
    return;
  }
  const servoId = row.dataset.servoId;
  const direction = Number(button.dataset.servoDelta);
  stopServoHold();
  nudgeServo(servoId, direction);
  servoHoldTimer = setInterval(() => nudgeServo(servoId, direction), 360);
}

function formatExecutionResult(result, options = {}) {
  const status = result.returnCode === 0 ? "完成" : "失败";
  const duration = Number.isFinite(result.durationSeconds) ? ` · ${result.durationSeconds}s` : "";
  const runMode = result.runMode === "local" ? " · 本机脚本" : "";
  const target = result.host ? ` · ${result.user || "root"}@${result.host}:${result.port}` : "";
  const header = `${status} · 返回码 ${result.returnCode}${duration}${runMode}${target}`;
  const stderr = cleanRemoteOutput(result.stderr);

  if (options.actionId === "read_positions") {
    const positions = servoPositionLines(parseServoPositions(result.stdout));
    if (positions.length > 0) {
      return [`舵机当前位置`, positions.join("\n"), header, stderr ? `错误输出\n${stderr}` : ""]
        .filter(Boolean)
        .join("\n\n");
    }
  }

  const stdout = cleanRemoteOutput(result.stdout);
  return [header, stdout ? `输出\n${stdout}` : "", stderr ? `错误输出\n${stderr}` : ""]
    .filter(Boolean)
    .join("\n\n");
}

function sceneExtraInputId(sceneId) {
  return `extra-${sceneId}`;
}

function scenePayload(sceneId) {
  const input = document.getElementById(sceneExtraInputId(sceneId));
  return {
    ...connectionPayload(),
    extraArgs: input ? input.value.trim() : "",
  };
}

async function previewScene(scene) {
  const data = await fetchJson(`/api/preview/${encodeURIComponent(scene.id)}`, {
    method: "POST",
    body: JSON.stringify(scenePayload(scene.id)),
  });
  showOutput(`${scene.number} ${scene.title} · 预览`, data.script);
}

async function runScene(scene) {
  const data = await fetchJson(`/api/run/${encodeURIComponent(scene.id)}`, {
    method: "POST",
    body: JSON.stringify(scenePayload(scene.id)),
  });
  showOutput(`${scene.number} ${scene.title} · 已加入队列`, queueItemSummary(data.queued));
  await refreshState();
}

async function previewQuick(action) {
  const data = await fetchJson(`/api/quick-action/${encodeURIComponent(action.id)}`, {
    method: "POST",
    body: JSON.stringify({ ...connectionPayload(), preview: true }),
  });
  showOutput(`${action.title} · 预览`, data.script);
}

async function runQuick(action) {
  if (action.emergency) {
    await runEmergencyStop(action);
    return;
  }
  const data = await fetchJson(`/api/quick-action/${encodeURIComponent(action.id)}`, {
    method: "POST",
    body: JSON.stringify(connectionPayload()),
  });
  showOutput(`${action.title} · 已加入队列`, queueItemSummary(data.queued));
  await refreshState();
}

async function runEmergencyStop(action) {
  const data = await fetchJson("/api/emergency-stop", {
    method: "POST",
    body: JSON.stringify(connectionPayload()),
  });
  const resultText = formatExecutionResult(data.result, { actionId: action.id });
  const summary = [
    `本地中断进程: ${data.result.stoppedProcesses ?? 0}`,
    `清空等待队列: ${data.result.clearedQueueItems ?? 0}`,
    resultText,
  ]
    .filter(Boolean)
    .join("\n\n");
  showOutput(`${action.title} · 执行结果`, summary);
  await refreshState();
  await refreshServoPositions({ manual: true });
}

function queueStatusLabel(status) {
  const labels = {
    pending: "等待中",
    running: "执行中",
    done: "完成",
    failed: "失败",
    removed: "已删除",
    interrupted: "已中断",
  };
  return labels[status] || status;
}

function queueItemSummary(item) {
  if (!item) {
    return "已加入队列";
  }
  const target =
    item.runMode === "local"
      ? `执行: 本机脚本 -> ${item.user}@${item.host}:${item.port}`
      : `目标: ${item.user}@${item.host}:${item.port}`;
  return [
    `队列 ID: ${item.queueId}`,
    `项目: ${item.title}`,
    `状态: ${queueStatusLabel(item.status)}`,
    target,
  ].join("\n");
}

async function deleteQueueItem(queueId) {
  const data = await fetchJson(`/api/queue/${encodeURIComponent(queueId)}`, {
    method: "DELETE",
  });
  showOutput("执行队列 · 已删除", queueItemSummary(data.removed));
  await refreshState();
}

function renderQueue(state) {
  const items = state.queue || [];
  const pendingCount = items.filter((item) => item.status === "pending").length;
  if (state.running || pendingCount > 0) {
    queueSummary.textContent = state.running ? `执行中 · ${pendingCount} 个等待` : `${pendingCount} 个等待`;
  } else {
    queueSummary.textContent = "空闲";
  }

  queueList.innerHTML = "";
  if (items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "queue-empty";
    empty.textContent = "当前没有等待或执行中的动作。";
    queueList.appendChild(empty);
    return;
  }

  for (const item of items) {
    const row = document.createElement("article");
    row.className = `queue-item ${item.status}`;

    const text = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.title;
    const meta = document.createElement("span");
    meta.textContent = `${queueStatusLabel(item.status)} · ${item.kind} · ${item.user}@${item.host}:${item.port} · ${item.queuedAt}`;
    text.append(title, meta);
    row.appendChild(text);

    if (item.status === "pending") {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "queue-remove";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `删除 ${item.title}`);
      remove.addEventListener("click", () => wrap(() => deleteQueueItem(item.queueId)));
      row.appendChild(remove);
    }

    queueList.appendChild(row);
  }
}

function renderServoPositions(servoState = {}, { forceTargetSync = false } = {}) {
  const values = servoState.values || {};
  for (let index = 0; index < servoPositionEls.length; index += 1) {
    const value = values[String(index)];
    servoPositionEls[index].textContent = value === undefined ? "-" : String(value);
  }
  if (!servoControlInFlight && !servoControlPending) {
    syncServoTargets(values, { force: forceTargetSync });
  } else {
    renderServoControls();
  }

  if (servoState.running) {
    servoPositionSummary.textContent = "读取中...";
    return;
  }
  if (servoState.error) {
    servoPositionSummary.textContent = `读取失败：${servoState.error}`;
    return;
  }
  if (servoState.warning && servoState.updatedAt) {
    servoPositionSummary.textContent = `更新于 ${servoState.updatedAt}（已忽略尾部超时）`;
    return;
  }
  if (servoState.updatedAt) {
    servoPositionSummary.textContent = `更新于 ${servoState.updatedAt}`;
    return;
  }
  servoPositionSummary.textContent = "需要时手动刷新。";
}

async function refreshServoPositions({ manual = false } = {}) {
  if (servoRefreshInFlight || servoControlInFlight || servoControlPending) {
    return;
  }
  if (!manual && latestState && (latestState.running || (latestState.queue || []).length > 0)) {
    renderServoPositions({ ...(latestState.servoPositions || {}), running: false });
    return;
  }

  servoRefreshInFlight = true;
  try {
    const response = await fetch("/api/servo-positions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(connectionPayload()),
    });
    const data = await response.json();
    if (response.status === 409) {
      const current = latestState ? latestState.servoPositions : {};
      renderServoPositions({ ...(current || {}), running: false, error: "动作执行中，暂停刷新" });
      return;
    }
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || data.servoPositions?.error || `HTTP ${response.status}`);
    }
    renderServoPositions(data.servoPositions, { forceTargetSync: manual });
    if (manual) {
      showOutput("舵机当前位置 · 刷新完成", servoPositionLines(data.servoPositions.values || {}).join("\n"));
    }
    await refreshState();
  } catch (error) {
    renderServoPositions({ values: {}, running: false, error: error.message || String(error) });
    if (manual) {
      showOutput("舵机当前位置 · 读取失败", error.message || String(error));
    }
  } finally {
    servoRefreshInFlight = false;
  }
}

function maybeRenderLastResult(state) {
  const result = state.lastResult;
  if (!result) {
    return;
  }
  const key = result.queueId || `${result.at}:${result.kind}:${result.id}:${result.returnCode}`;
  if (key === lastRenderedResultKey) {
    return;
  }
  lastRenderedResultKey = key;
  showOutput(`${result.title} · 执行结果`, formatExecutionResult(result, { actionId: result.id }));
}

function renderScenes() {
  sceneGrid.innerHTML = "";
  for (const scene of registry.scenes) {
    const card = document.createElement("article");
    card.className = `scene-card ${scene.risk}`;
    card.innerHTML = `
      <div class="scene-top">
        <span class="scene-number">${scene.number}</span>
        <span class="risk">${riskLabel(scene.risk)}</span>
      </div>
      <h3>${scene.title}</h3>
      <p class="subtitle">${scene.subtitle}</p>
      <dl>
        <dt>Operator Cue</dt>
        <dd>${scene.operatorCue}</dd>
        <dt>Success</dt>
        <dd>${scene.successSignal}</dd>
        <dt>Fallback</dt>
        <dd>${scene.fallbackBehavior}</dd>
      </dl>
      <label class="extra-label">
        Extra Args
        <input id="${sceneExtraInputId(scene.id)}" type="text" placeholder="${scene.defaultArgs.join(" ")}" />
      </label>
      <div class="button-row">
        <button type="button" data-action="preview">预览命令</button>
        <button type="button" class="execute" data-action="run">加入队列</button>
      </div>
    `;
    card.querySelector('[data-action="preview"]').addEventListener("click", () => wrap(() => previewScene(scene)));
    card.querySelector('[data-action="run"]').addEventListener("click", () => wrap(() => runScene(scene)));
    sceneGrid.appendChild(card);
  }
}

function renderQuickActions() {
  const teachCard = document.getElementById("teach-motion-card");
  quickGrid.innerHTML = "";
  if (teachCard) {
    quickGrid.appendChild(teachCard);
  }
  for (const action of registry.quickActions) {
    const card = document.createElement("article");
    card.className = `quick-card ${action.risk}`;
    const runLabel = action.runLabel || (action.emergency ? "强停归位" : "入队");
    card.innerHTML = `
      <div>
        <strong>${action.title}</strong>
        <span>${riskLabel(action.risk)}</span>
      </div>
      <div class="button-row">
        <button type="button" data-action="preview">预览</button>
        <button type="button" class="execute ${action.emergency ? "emergency" : ""}" data-action="run">${runLabel}</button>
      </div>
    `;
    card.querySelector('[data-action="preview"]').addEventListener("click", () => wrap(() => previewQuick(action)));
    card.querySelector('[data-action="run"]').addEventListener("click", () => wrap(() => runQuick(action)));
    quickGrid.appendChild(card);
  }
}

function renderLightShowcase() {
  if (!lightShowcaseGrid) {
    return;
  }
  lightShowcaseGrid.innerHTML = "";
  const actionsById = new Map((registry.quickActions || []).map((action) => [action.id, action]));
  for (const actionId of LIGHT_SHOWCASE_IDS) {
    const action = actionsById.get(actionId);
    if (!action || action.risk !== "light-only") {
      continue;
    }
    const card = document.createElement("article");
    card.className = `quick-card light-showcase-card ${action.risk}`;
    const runLabel = action.id === "led_off" ? "关灯" : "点亮";
    card.innerHTML = `
      <div>
        <strong>${action.title}</strong>
        <span>${riskLabel(action.risk)}</span>
      </div>
      <div class="button-row">
        <button type="button" data-action="preview">预览</button>
        <button type="button" class="execute" data-action="run">${runLabel}</button>
      </div>
    `;
    card.querySelector('[data-action="preview"]').addEventListener("click", () => wrap(() => previewQuick(action)));
    card.querySelector('[data-action="run"]').addEventListener("click", () => wrap(() => runQuick(action)));
    lightShowcaseGrid.appendChild(card);
  }
}

async function refreshState() {
  const data = await fetchJson("/api/state");
  const state = data.state;
  latestState = state;
  running.textContent = state.running ? "running" : "idle";
  current.textContent = state.current ? `${state.current.kind}:${state.current.title}` : "-";
  lastCode.textContent = state.lastResult ? String(state.lastResult.returnCode) : "-";
  renderQueue(state);
  renderServoPositions(state.servoPositions);
  renderTeachMotion(state.teachMotion || {});
  maybeRenderLastResult(state);
}

async function load() {
  const data = await fetchJson("/api/scenes");
  registry = data.registry;
  hostInput.value = data.defaults.host;
  portInput.value = data.defaults.port;
  userInput.value = data.defaults.user;
  boardSummary.textContent = `${data.defaults.user}@${data.defaults.host}:${data.defaults.port}`;
  passwordSummary.textContent = data.passwordConfigured ? "password: env configured" : "password: optional";
  renderScenes();
  renderQuickActions();
  renderLightShowcase();
  await refreshState();
  checkConnection({ quiet: true }).catch(() => {});
  refreshCamera().catch(() => {});
  refreshBookFollow().catch(() => {});
  checkTouchAudio({ quiet: true }).catch(() => {});
  refreshShow().catch(() => {});
  refreshPrinterHealth().catch(() => {});
  refreshReprintJobs().catch(() => {});
}

async function wrap(fn) {
  try {
    showOutput("执行中", "Working...");
    await fn();
  } catch (error) {
    showOutput("错误", error.message || String(error));
  }
}

document.getElementById("refresh").addEventListener("click", () => wrap(refreshState));
lightShowcaseRefreshButton.addEventListener("click", () => wrap(refreshState));
connectionCheckButton.addEventListener("click", () => wrap(() => checkConnection()));
refreshServosButton.addEventListener("click", () => wrap(() => refreshServoPositions({ manual: true })));
cameraStartButton.addEventListener("click", () => wrap(() => cameraAction("/api/camera/watch/start", "摄像头 · 已开启刷新")));
cameraStopButton.addEventListener("click", () => wrap(() => cameraAction("/api/camera/watch/stop", "摄像头 · 已暂停刷新")));
cameraCaptureButton.addEventListener("click", () => wrap(() => cameraAction("/api/camera/capture", "摄像头 · 抓取完成")));
cameraRenderPrintLatestButton.addEventListener("click", () => wrap(cameraRenderPrintLatestAction));
cameraReprintLatestRenderButton.addEventListener("click", () => wrap(cameraReprintLatestRenderAction));
bookFollowStartButton.addEventListener("click", () => wrap(() => bookFollowAction("/api/book-follow/start", "追书 · 已启动")));
bookFollowStopButton.addEventListener("click", () => wrap(() => bookFollowAction("/api/book-follow/stop", "追书 · 已停止")));
bookFollowRefreshButton.addEventListener("click", () => wrap(refreshBookFollow));
for (const button of showStepButtons) {
  button.addEventListener("click", () => wrap(() => showStepAction(button.dataset.showStep)));
}
showResetButton.addEventListener("click", () => wrap(resetShow));
for (const button of voiceMotionDemoButtons) {
  button.addEventListener("click", () => wrap(() => voiceMotionDemoAction(button.dataset.voiceMotionDemo)));
}
openCelebrationPageButton.addEventListener("click", () => wrap(openCelebrationPage));
touchStopButton.addEventListener("click", () => wrap(() => touchAction("stop", "摸摸系统 · 临时关闭")));
touchStartButton.addEventListener("click", () => wrap(() => touchAction("start", "摸摸系统 · 临时启动")));
touchDisableButton.addEventListener("click", () => wrap(() => touchAction("disable-autostart", "摸摸系统 · 关闭开机自启")));
touchEnableButton.addEventListener("click", () => wrap(() => touchAction("enable-autostart", "摸摸系统 · 恢复开机自启")));
touchAudioCheckButton.addEventListener("click", () => wrap(() => checkTouchAudio({ boardCheck: true, testAudio: true })));
narrationPlayButton.addEventListener("click", () => wrap(narrationAction));
teachStartButton.addEventListener("click", () => wrap(() => teachMotionAction("start", "示教录制 · 已开始")));
teachStopButton.addEventListener("click", () => wrap(() => teachMotionAction("stop", "示教录制 · 已结束")));
teachPlayButton.addEventListener("click", () => wrap(() => teachMotionAction("play", "示教录制 · 回放完成")));
for (const button of touchSensitivityButtons) {
  button.addEventListener("click", () => wrap(() => touchSensitivityAction(button.dataset.touchPreset)));
}
document.getElementById("clear-output").addEventListener("click", () => showOutput("等待操作", ""));
for (const button of servoControlButtons) {
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    startServoHold(button);
  });
  button.addEventListener("pointerup", stopServoHold);
  button.addEventListener("pointercancel", stopServoHold);
  button.addEventListener("pointerleave", stopServoHold);
}
window.addEventListener("pointerup", stopServoHold);
servoStepInput.addEventListener("change", () => {
  servoStepInput.value = String(servoStepSize());
});

wrap(load);
setInterval(() => {
  refreshState().catch(() => {});
}, 1500);
setInterval(() => {
  refreshShow().catch(() => {});
}, 1500);
setInterval(() => {
  refreshCamera().catch(() => {});
}, 2000);
setInterval(() => {
  refreshBookFollow().catch(() => {});
}, 2500);
setInterval(() => {
  checkTouchAudio({ quiet: true }).catch(() => {});
}, 20000);
setInterval(() => {
  refreshPrinterHealth().catch(() => {});
}, 5000);
setInterval(() => {
  refreshReprintJobs().catch(() => {});
}, 3000);
