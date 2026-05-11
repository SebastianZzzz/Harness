import "./styles/dashboard.css";

const STORAGE_KEY = "aegis.activeTaskId";
const TASK_ENDPOINT = "/api/v1/tasks";
const HEALTH_ENDPOINT = "/health";
const TARGET_REPO = "AegisHarness-Demo";

const PHASES = [
  {
    key: "1_INTENT_PARSING",
    step: "01",
    title: "Intake",
    copy: "Parse the request into a structured prompt skeleton.",
    view: "workflow",
  },
  {
    key: "2_PRECHECK_GREPTILE",
    step: "02",
    title: "Context fetch",
    copy: "Search for similar repos and extract constraints.",
    view: "workflow",
  },
  {
    key: "3_HUMAN_IN_THE_LOOP",
    step: "03",
    title: "Approval",
    copy: "Reviewer confirms the structured prompt is safe.",
    view: "approval",
  },
  {
    key: "4_COMPUTE_ROUTING",
    step: "04",
    title: "Code gen",
    copy: "Model writes the implementation against constraints.",
    view: "output",
  },
  {
    key: "5_SANDBOX_TESTING",
    step: "05",
    title: "Sandbox",
    copy: "Run, review, retry up to 3x until checks pass.",
    view: "logs",
  },
];

const EMPTY_TASK = {
  id: "",
  original_prompt: "",
  structured_prompt: "",
  bug_list_constraints: [],
  current_phase: "1_INTENT_PARSING",
  search_provider: "github",
  difficulty_score: null,
  selected_model: "",
  generated_code: "",
  sandbox_iterations: 0,
  max_iterations: 3,
  created_at: "",
  updated_at: "",
};

const state = {
  activeView: "workflow",
  backendConnected: false,
  autoRefresh: true,
  tailFollow: true,
  loading: false,
  ws: null,
  task: { ...EMPTY_TASK },
  draftPrompt: "",
  draftSearchProvider: "github",
  taskLookup: "",
  logs: [],
  stream: [],
  prUrl: "",
  phaseDurations: {},
};

const els = {};
let refreshTimer = null;

document.addEventListener("DOMContentLoaded", async () => {
  captureElements();
  bindEvents();
  render();
  await checkBackendHealth();
  await hydrateStoredTask();
  refreshTimer = window.setInterval(() => {
    if (state.autoRefresh && state.task.id) {
      void loadTask(state.task.id, { silent: true });
    }
  }, 5000);
});

function captureElements() {
  els.views = {
    workflow: document.getElementById("view-workflow"),
    approval: document.getElementById("view-approval"),
    output: document.getElementById("view-output"),
    logs: document.getElementById("view-logs"),
  };

  els.taskIdInput = document.getElementById("task-id-input");
  els.taskRequest = document.getElementById("task-request");
  els.searchProvider = document.getElementById("search-provider");
  els.backendStatusPill = document.getElementById("backend-status-pill");
  els.backendStatusDot = document.getElementById("backend-status-dot");
  els.backendStatusLabel = document.getElementById("backend-status-label");
  els.workflowCount = document.getElementById("workflow-count");
  els.logsLiveIndicator = document.getElementById("logs-live-indicator");

  els.workflowPhaseChip = document.getElementById("workflow-phase-chip");
  els.retryChip = document.getElementById("retry-chip");
  els.snapshotPhaseTitle = document.getElementById("snapshot-phase-title");
  els.snapshotPhaseCopy = document.getElementById("snapshot-phase-copy");
  els.snapshotTaskId = document.getElementById("snapshot-task-id");
  els.snapshotProvider = document.getElementById("snapshot-provider");
  els.snapshotModel = document.getElementById("snapshot-model");
  els.snapshotConstraints = document.getElementById("snapshot-constraints");
  els.snapshotUpdated = document.getElementById("snapshot-updated");
  els.taskHealthChip = document.getElementById("task-health-chip");
  els.phaseGrid = document.getElementById("phase-grid");

  els.promptTitle = document.getElementById("prompt-title");
  els.promptMetaChip = document.getElementById("prompt-meta-chip");
  els.promptSurface = document.getElementById("prompt-surface");
  els.reviewList = document.getElementById("review-list");
  els.constraintTitle = document.getElementById("constraint-title");
  els.constraintSummaryChip = document.getElementById("constraint-summary-chip");
  els.approvalHeaderChip = document.getElementById("approval-header-chip");
  els.approvalEditor = document.getElementById("approval-editor");

  els.outputStatusChip = document.getElementById("output-status-chip");
  els.outputModel = document.getElementById("output-model");
  els.outputModelCopy = document.getElementById("output-model-copy");
  els.outputPhase = document.getElementById("output-phase");
  els.outputPhaseCopy = document.getElementById("output-phase-copy");
  els.outputIterations = document.getElementById("output-iterations");
  els.outputIterationsBar = document.getElementById("output-iterations-bar");
  els.outputProvider = document.getElementById("output-provider");
  els.outputProviderCopy = document.getElementById("output-provider-copy");
  els.deliveryState = document.getElementById("delivery-state");
  els.outputTaskId = document.getElementById("output-task-id");
  els.outputConstraintTotal = document.getElementById("output-constraint-total");
  els.outputSandbox = document.getElementById("output-sandbox");
  els.outputBranch = document.getElementById("output-branch");
  els.outputUpdated = document.getElementById("output-updated");
  els.phaseLogList = document.getElementById("phase-log-list");
  els.generatedCode = document.getElementById("generated-code");
  els.viewDiff = document.getElementById("view-diff");
  els.openPr = document.getElementById("open-pr");

  els.logsStatusTitle = document.getElementById("logs-status-title");
  els.logsHealthChip = document.getElementById("logs-health-chip");
  els.logsTaskId = document.getElementById("logs-task-id");
  els.logsProvider = document.getElementById("logs-provider");
  els.logsIterations = document.getElementById("logs-iterations");
  els.logsUpdated = document.getElementById("logs-updated");
  els.logsRepoTitle = document.getElementById("logs-repo-title");
  els.logsBranchChip = document.getElementById("logs-branch-chip");
  els.logsModel = document.getElementById("logs-model");
  els.logsConstraintCount = document.getElementById("logs-constraint-count");
  els.logsPrStatus = document.getElementById("logs-pr-status");
  els.logsSandbox = document.getElementById("logs-sandbox");
  els.eventMixTitle = document.getElementById("event-mix-title");
  els.mixInfoBar = document.getElementById("mix-info-bar");
  els.mixOkBar = document.getElementById("mix-ok-bar");
  els.mixReviewBar = document.getElementById("mix-review-bar");
  els.mixErrorBar = document.getElementById("mix-error-bar");
  els.mixInfoCount = document.getElementById("mix-info-count");
  els.mixOkCount = document.getElementById("mix-ok-count");
  els.mixReviewCount = document.getElementById("mix-review-count");
  els.mixErrorCount = document.getElementById("mix-error-count");
  els.terminalTitle = document.getElementById("terminal-title");
  els.terminalOutput = document.getElementById("terminal-output");
  els.pipelineTotalDuration = document.getElementById("pipeline-total-duration");
  els.pipelineIterationStatus = document.getElementById("pipeline-iteration-status");
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setActiveView(button.dataset.view));
  });

  els.taskIdInput.addEventListener("input", (event) => {
    state.taskLookup = event.target.value.trim();
  });

  els.taskRequest.addEventListener("input", (event) => {
    state.draftPrompt = event.target.value;
  });

  els.searchProvider.addEventListener("change", (event) => {
    state.draftSearchProvider = event.target.value;
  });

  document.getElementById("copy-task-id").addEventListener("click", copyTaskId);
  document.getElementById("refresh-task").addEventListener("click", refreshTask);
  document.getElementById("load-task").addEventListener("click", () => {
    if (state.taskLookup) {
      void loadTask(state.taskLookup, { silent: false });
    }
  });
  document.getElementById("create-task").addEventListener("click", createTask);
  document.getElementById("approve-task-header").addEventListener("click", () => void submitApproval(true));
  document.getElementById("reject-task-header").addEventListener("click", () => void submitApproval(false));
  document.getElementById("copy-generated-code").addEventListener("click", copyGeneratedCode);
  document.getElementById("view-diff").addEventListener("click", openDiff);
  document.getElementById("open-pr").addEventListener("click", openPr);
  document.getElementById("toggle-auto-refresh").addEventListener("click", toggleAutoRefresh);
  document.getElementById("export-log").addEventListener("click", exportLogs);
  document.getElementById("toggle-tail-follow").addEventListener("click", toggleTailFollow);
}

async function checkBackendHealth() {
  try {
    const response = await fetch(HEALTH_ENDPOINT);
    state.backendConnected = response.ok;
  } catch {
    state.backendConnected = false;
  }
  renderBackendStatus();
}

async function hydrateStoredTask() {
  const storedTaskId = localStorage.getItem(STORAGE_KEY);
  if (!storedTaskId) {
    render();
    return;
  }
  state.taskLookup = storedTaskId;
  els.taskIdInput.value = storedTaskId;
  await loadTask(storedTaskId, { silent: true });
}

function setActiveView(view) {
  state.activeView = view;
  renderViews();
}

function render() {
  renderViews();
  renderBackendStatus();
  renderSidebarState();
  renderTaskControls();
  renderWorkflow();
  renderApproval();
  renderOutput();
  renderLogs();
}

function renderViews() {
  Object.entries(els.views).forEach(([key, node]) => {
    node.classList.toggle("is-active", key === state.activeView);
  });
  document.querySelectorAll(".sidebar-link").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === state.activeView);
  });
}

function renderBackendStatus() {
  els.backendStatusPill.classList.toggle("is-offline", !state.backendConnected);
  els.backendStatusDot.classList.toggle("is-offline", !state.backendConnected);
  els.backendStatusLabel.textContent = state.backendConnected ? "Backend connected" : "Backend unavailable";
}

function renderSidebarState() {
  els.workflowCount.textContent = state.task.id ? "1" : "0";
  els.logsLiveIndicator.textContent = state.ws && state.ws.readyState === WebSocket.OPEN ? "live" : "idle";
  els.logsLiveIndicator.classList.toggle("is-live", state.ws && state.ws.readyState === WebSocket.OPEN);
}

function renderTaskControls() {
  if (document.activeElement !== els.taskIdInput) {
    els.taskIdInput.value = state.taskLookup;
  }
  if (document.activeElement !== els.taskRequest) {
    els.taskRequest.value = state.draftPrompt;
  }
  els.searchProvider.value = state.draftSearchProvider;
}

function renderWorkflow() {
  els.workflowPhaseChip.textContent = workflowPhaseLabel();
  els.retryChip.textContent = `${state.task.max_iterations} / retries`;
  els.snapshotPhaseTitle.textContent = workflowPhaseShort();
  els.snapshotPhaseCopy.textContent = workflowPhaseCopy();
  els.snapshotTaskId.textContent = state.task.id ? compactTaskId(state.task.id) : "Not loaded";
  els.snapshotProvider.textContent = formatProvider(state.task.search_provider);
  els.snapshotModel.textContent = state.task.selected_model || "Pending";
  els.snapshotConstraints.textContent = `${state.task.bug_list_constraints.length} active`;
  els.snapshotUpdated.textContent = formatTime(state.task.updated_at);
  els.taskHealthChip.textContent = taskHealthLabel();
  els.taskHealthChip.className = healthChipClass();
  els.pipelineIterationStatus.textContent = `iter ${state.task.sandbox_iterations} / ${state.task.max_iterations}`;
  els.pipelineTotalDuration.textContent = `Duration ${totalDurationLabel()}`;

  els.phaseGrid.innerHTML = PHASES.map((phase, index) => {
    const status = phaseStatus(phase.key);
    const active = state.activeView === phase.view;
    return `
      <button class="phase-card ${active ? "phase-card--active" : ""}" type="button" data-phase-view="${phase.view}">
        <div class="phase-card-head">
          <span class="phase-step">${phase.step}</span>
          <span class="phase-status ${phaseStatusClass(status)}">${status}</span>
        </div>
        <div class="phase-card-title">${escapeHtml(phase.title)}</div>
        <div class="phase-card-copy">${escapeHtml(phase.copy)}</div>
        <div class="phase-progress"><span style="width:${phaseProgress(index)}%"></span></div>
        <div class="phase-meta">
          <span>Latency</span>
          <strong>${phaseLatency(phase.key)}</strong>
        </div>
      </button>
    `;
  }).join("");

  document.querySelectorAll("[data-phase-view]").forEach((button) => {
    button.addEventListener("click", () => setActiveView(button.dataset.phaseView));
  });
}

function renderApproval() {
  const constraints = state.task.bug_list_constraints || [];
  els.approvalHeaderChip.textContent = approvalHeaderText();
  els.approvalHeaderChip.className = approvalHeaderClass();
  els.promptTitle.textContent = "Generated by planner · Phase 2";
  els.promptMetaChip.textContent = `${formatProvider(state.task.search_provider)} · similar-repo`;
  els.constraintTitle.textContent = `Constraints · ${constraints.length} active`;
  els.constraintSummaryChip.textContent = constraints.length
    ? (phaseIndex(state.task.current_phase) >= phaseIndex("4_COMPUTE_ROUTING") ? "all passed" : "review ready")
    : "waiting";
  els.promptSurface.innerHTML = renderPromptDocument(state.task.structured_prompt || state.task.original_prompt);
  if (document.activeElement !== els.approvalEditor) {
    els.approvalEditor.value = state.task.structured_prompt || "";
  }

  els.reviewList.innerHTML = constraints.length
    ? constraints.map((constraint, index) => `
        <article class="checklist-item">
          <div class="checklist-mark ${phaseIndex(state.task.current_phase) >= phaseIndex("4_COMPUTE_ROUTING") ? "checklist-mark--filled" : ""}">
            ${phaseIndex(state.task.current_phase) >= phaseIndex("4_COMPUTE_ROUTING") ? "✓" : ""}
          </div>
          <div class="checklist-copy">${escapeHtml(constraint)}</div>
          <div class="checklist-pill">${phaseIndex(state.task.current_phase) >= phaseIndex("4_COMPUTE_ROUTING") ? "PASS" : "ACTIVE"}</div>
        </article>
      `).join("")
    : `<div class="empty-state">No constraint pack is available yet.</div>`;
}

function renderOutput() {
  els.outputStatusChip.textContent = outputStatusLabel();
  els.outputStatusChip.className = outputStatusClass();
  els.outputModel.textContent = state.task.selected_model || "Pending";
  els.outputModelCopy.textContent = state.task.selected_model
    ? "Picked during Phase 4 routing."
    : "No model has been selected yet.";
  els.outputPhase.textContent = outputPhaseLabel();
  els.outputPhaseCopy.textContent = phaseDescription(state.task.current_phase);
  els.outputIterations.textContent = `${state.task.sandbox_iterations} / ${state.task.max_iterations}`;
  els.outputIterationsBar.style.width = `${iterationProgress()}%`;
  els.outputProvider.textContent = formatProvider(state.task.search_provider);
  els.outputProviderCopy.textContent = state.task.id ? "Context gathered from similar repositories." : "No similar repositories loaded yet.";
  els.deliveryState.textContent = state.task.generated_code ? "Code generated" : "Awaiting code";
  els.outputTaskId.textContent = state.task.id ? compactTaskId(state.task.id) : "Not loaded";
  els.outputConstraintTotal.textContent = String(state.task.bug_list_constraints.length);
  els.outputSandbox.textContent = TARGET_REPO;
  els.outputBranch.textContent = prBranchLabel();
  els.outputUpdated.textContent = formatTime(state.task.updated_at);
  els.generatedCode.textContent = state.task.generated_code || "# Generated code appears here after Phase 4.";

  els.viewDiff.disabled = !state.prUrl;
  els.openPr.disabled = !state.prUrl;

  els.phaseLogList.innerHTML = phaseLogEntries().length
    ? phaseLogEntries().map((entry) => `
        <div class="phase-log-item">
          <span>${escapeHtml(entry.time)}</span>
          <strong>${escapeHtml(entry.text)}</strong>
        </div>
      `).join("")
    : `<div class="empty-state">No phase log has been emitted yet.</div>`;
}

function renderLogs() {
  els.logsStatusTitle.textContent = logsStatusTitle();
  els.logsHealthChip.textContent = taskHealthLabel();
  els.logsHealthChip.className = healthChipClass();
  els.logsTaskId.textContent = state.task.id ? compactTaskId(state.task.id) : "Not loaded";
  els.logsProvider.textContent = formatProvider(state.task.search_provider);
  els.logsIterations.textContent = `${state.task.sandbox_iterations} / ${state.task.max_iterations}`;
  els.logsUpdated.textContent = formatTime(state.task.updated_at);
  els.logsRepoTitle.textContent = TARGET_REPO;
  els.logsBranchChip.textContent = prBranchLabel();
  els.logsModel.textContent = state.task.selected_model || "Pending";
  els.logsConstraintCount.textContent = String(state.task.bug_list_constraints.length);
  els.logsPrStatus.textContent = state.prUrl ? "open" : "Not opened";
  els.logsSandbox.textContent = TARGET_REPO;
  els.terminalTitle.textContent = state.task.id ? `~ aegis · stream://task/${state.task.id.slice(0, 8)}` : "~ aegis · stream://task/not-loaded";
  document.getElementById("toggle-auto-refresh").textContent = `Auto-refresh · ${state.autoRefresh ? "on" : "off"}`;

  const mix = eventMix();
  els.eventMixTitle.textContent = `${mix.total} events`;
  updateMixRow(els.mixInfoBar, els.mixInfoCount, mix.info, mix.total);
  updateMixRow(els.mixOkBar, els.mixOkCount, mix.ok, mix.total);
  updateMixRow(els.mixReviewBar, els.mixReviewCount, mix.review, mix.total);
  updateMixRow(els.mixErrorBar, els.mixErrorCount, mix.error, mix.total);

  els.terminalOutput.innerHTML = state.logs.length
    ? state.logs.map((entry) => `
        <div class="terminal-line">
          <span class="terminal-time">${escapeHtml(entry.time)}</span>
          <span class="terminal-level terminal-level--${entry.levelClass}">${escapeHtml(entry.level)}</span>
          <span class="terminal-message">${escapeHtml(entry.message)}</span>
        </div>
      `).join("")
    : `<div class="empty-state">No execution logs yet.</div>`;

  if (state.tailFollow) {
    requestAnimationFrame(() => {
      els.terminalOutput.scrollTop = els.terminalOutput.scrollHeight;
    });
  }
}

async function createTask() {
  const prompt = state.draftPrompt.trim();
  if (!prompt || state.loading) {
    return;
  }

  state.loading = true;
  try {
    const params = new URLSearchParams({
      prompt,
      search_provider: state.draftSearchProvider,
    });
    const response = await fetch(`${TASK_ENDPOINT}/?${params.toString()}`, { method: "POST" });
    if (!response.ok) {
      throw new Error(`Task creation failed with status ${response.status}`);
    }
    const task = normalizeTask(await response.json());
    applyTask(task);
    state.backendConnected = true;
    connectTaskSocket(task.id);
    localStorage.setItem(STORAGE_KEY, task.id);
    pushStream("Task created", "Planner accepted the request and started the workflow.", ["PHASE", "TASK"]);
    pushLog(`Task ${task.id} created`, "INFO");
    setActiveView("workflow");
  } catch (error) {
    state.backendConnected = false;
    pushLog(error.message, "ERROR");
  } finally {
    state.loading = false;
    render();
  }
}

async function refreshTask() {
  if (!state.task.id) {
    return;
  }
  await loadTask(state.task.id, { silent: true });
}

async function loadTask(taskId, options = { silent: false }) {
  try {
    const response = await fetch(`${TASK_ENDPOINT}/${encodeURIComponent(taskId)}`);
    if (!response.ok) {
      throw new Error(`Task lookup failed with status ${response.status}`);
    }
    const task = normalizeTask(await response.json());
    applyTask(task);
    state.backendConnected = true;
    connectTaskSocket(task.id);
    localStorage.setItem(STORAGE_KEY, task.id);
    if (!options.silent) {
      pushStream("Task loaded", "Loaded the latest task state from the backend.", ["TASK", "LOAD"]);
    }
  } catch (error) {
    state.backendConnected = false;
    pushLog(error.message, "ERROR");
  } finally {
    render();
  }
}

async function submitApproval(approved) {
  if (!state.task.id) {
    return;
  }
  try {
    const editedPrompt = els.approvalEditor.value.trim();
    const response = await fetch(`${TASK_ENDPOINT}/${encodeURIComponent(state.task.id)}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approved,
        edited_prompt: approved && editedPrompt ? editedPrompt : null,
      }),
    });
    if (!response.ok) {
      throw new Error(`Approval request failed with status ${response.status}`);
    }
    const task = normalizeTask(await response.json());
    applyTask(task);
    pushStream(
      approved ? "Approval granted" : "Task rejected",
      approved ? "Phase 4 can now execute." : "The workflow was rejected before generation.",
      ["APPROVAL"]
    );
    pushLog(approved ? "Approval granted" : "Task rejected", approved ? "OK" : "REVIEW");
    setActiveView(approved ? "output" : "workflow");
  } catch (error) {
    pushLog(error.message, "ERROR");
  } finally {
    render();
  }
}

function connectTaskSocket(taskId) {
  if (!taskId) {
    return;
  }

  if (state.ws) {
    state.ws.close();
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  state.ws = new WebSocket(`${protocol}://${window.location.host}/ws/tasks/${taskId}`);

  state.ws.addEventListener("open", () => {
    pushLog("WS connected", "INFO");
    renderSidebarState();
  });

  state.ws.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data);
      handleSocketMessage(payload);
    } catch {
      pushLog("Failed to parse socket payload", "ERROR");
      render();
    }
  });

  state.ws.addEventListener("close", () => {
    renderSidebarState();
  });
}

function handleSocketMessage(payload) {
  if (payload.type === "system") {
    pushLog(payload.message, "INFO");
  }

  if (payload.type === "log") {
    pushLog(payload.message, inferLevel(payload.message));
    extractPrUrl(payload.message);
  }

  if (payload.type === "state_change") {
    state.task = {
      ...state.task,
      current_phase: payload.phase || state.task.current_phase,
      selected_model: payload.data?.selected_model || state.task.selected_model,
      generated_code: payload.data?.code || state.task.generated_code,
      updated_at: new Date().toISOString(),
    };
    pushStream("Phase changed", `Task advanced to ${phaseHeadline(state.task.current_phase)}.`, ["PHASE"]);
    pushLog(`Task advanced to ${phaseHeadline(state.task.current_phase)}`, "PHASE");
  }

  render();
}

function applyTask(task) {
  state.task = task;
  state.taskLookup = task.id || "";
  state.draftPrompt = task.original_prompt || "";
  state.draftSearchProvider = task.search_provider || "github";
  if (!state.prUrl) {
    state.prUrl = "";
  }
}

function normalizeTask(task) {
  return {
    ...EMPTY_TASK,
    ...task,
    bug_list_constraints: Array.isArray(task.bug_list_constraints) ? task.bug_list_constraints : [],
    generated_code: task.generated_code || "",
    structured_prompt: task.structured_prompt || task.original_prompt || "",
  };
}

function copyTaskId() {
  if (!state.task.id) {
    return;
  }
  void navigator.clipboard.writeText(state.task.id);
}

function copyGeneratedCode() {
  if (!state.task.generated_code) {
    return;
  }
  void navigator.clipboard.writeText(state.task.generated_code);
}

function openPr() {
  if (state.prUrl) {
    window.open(state.prUrl, "_blank", "noopener,noreferrer");
  }
}

function openDiff() {
  if (state.prUrl) {
    window.open(`${state.prUrl}/files`, "_blank", "noopener,noreferrer");
  }
}

function toggleAutoRefresh() {
  state.autoRefresh = !state.autoRefresh;
  render();
}

function toggleTailFollow() {
  state.tailFollow = !state.tailFollow;
  document.getElementById("toggle-tail-follow").textContent = state.tailFollow ? "Tail follow" : "Tail paused";
}

function exportLogs() {
  const content = state.logs.map((entry) => `[${entry.time}] ${entry.level} ${entry.message}`).join("\n");
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "task-execution.log";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function pushStream(title, copy, tags) {
  state.stream.unshift({
    title,
    copy,
    tags,
  });
  state.stream = state.stream.slice(0, 12);
}

function pushLog(message, level) {
  const now = new Date();
  state.logs.push({
    time: now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    level,
    levelClass: level.toLowerCase(),
    message,
  });
  state.logs = state.logs.slice(-200);
}

function extractPrUrl(message) {
  const match = message.match(/https:\/\/github\.com\/[^\s]+/);
  if (match) {
    state.prUrl = match[0];
  }
}

function inferLevel(message) {
  const text = message.toLowerCase();
  if (text.includes("error") || text.includes("fail") || text.includes("issue") || text.includes("timeout")) {
    return "ERROR";
  }
  if (text.includes("review") || text.includes("approval")) {
    return "REVIEW";
  }
  if (text.includes("pass") || text.includes("approved") || text.includes("merged") || text.includes("opened")) {
    return "OK";
  }
  return "INFO";
}

function phaseStatus(phaseKey) {
  if (state.task.current_phase === "FAILED") {
    const currentIndex = phaseIndex(state.task.current_phase);
    const phaseIndexValue = phaseIndex(phaseKey);
    if (phaseIndexValue < currentIndex) return "DONE";
    if (phaseIndexValue === currentIndex) return "FAILED";
    return "BLOCKED";
  }
  if (state.task.current_phase === "FINISHED") {
    return "DONE";
  }
  const currentIndex = phaseIndex(state.task.current_phase);
  const phaseIndexValue = phaseIndex(phaseKey);
  if (phaseIndexValue < currentIndex) return "DONE";
  if (phaseIndexValue === currentIndex) return "RUNNING";
  return "PENDING";
}

function phaseStatusClass(status) {
  return {
    DONE: "phase-status--done",
    RUNNING: "phase-status--running",
    PENDING: "phase-status--pending",
    FAILED: "phase-status--failed",
    BLOCKED: "phase-status--pending",
  }[status];
}

function phaseProgress(index) {
  const currentIndex = phaseIndex(state.task.current_phase);
  if (state.task.current_phase === "FINISHED") return 100;
  if (index < currentIndex) return 100;
  if (index === currentIndex) return state.task.current_phase === "3_HUMAN_IN_THE_LOOP" ? 42 : 58;
  return 8;
}

function phaseIndex(key) {
  const order = PHASES.map((item) => item.key).concat(["FINISHED", "FAILED"]);
  const index = order.indexOf(key);
  return index === -1 ? 0 : index;
}

function phaseLatency(phaseKey) {
  return state.phaseDurations[phaseKey] || "—";
}

function workflowPhaseLabel() {
  if (!state.task.id) return "No active task";
  const phase = phaseHeadline(state.task.current_phase).toUpperCase();
  const status = state.task.current_phase === "FINISHED" ? "DONE" : state.task.current_phase === "FAILED" ? "FAILED" : "RUNNING";
  return `${phase} · ${status}`;
}

function workflowPhaseShort() {
  if (!state.task.id) return "No active task";
  if (state.task.current_phase === "FINISHED") return "Finished";
  if (state.task.current_phase === "FAILED") return "Failed";
  return `Phase ${phaseIndex(state.task.current_phase) + 1}`;
}

function workflowPhaseCopy() {
  return phaseDescription(state.task.current_phase);
}

function phaseDescription(phase) {
  const descriptions = {
    "1_INTENT_PARSING": "Request intake in progress.",
    "2_PRECHECK_GREPTILE": "Constraint analysis in progress.",
    "3_HUMAN_IN_THE_LOOP": "Approval waiting on reviewer input.",
    "4_COMPUTE_ROUTING": "Code generation in flight.",
    "5_SANDBOX_TESTING": "Sandbox review and PR flow in progress.",
    FINISHED: "Backend marked task complete.",
    FAILED: "Task stopped before completion.",
  };
  return descriptions[phase] || "Status unavailable.";
}

function phaseHeadline(phase) {
  const labels = {
    "1_INTENT_PARSING": "Phase 1",
    "2_PRECHECK_GREPTILE": "Phase 2",
    "3_HUMAN_IN_THE_LOOP": "Phase 3",
    "4_COMPUTE_ROUTING": "Phase 4",
    "5_SANDBOX_TESTING": "Phase 5",
    FINISHED: "Finished",
    FAILED: "Failed",
  };
  return labels[phase] || "Unknown";
}

function taskHealthLabel() {
  if (!state.task.id) return "Idle";
  return state.task.current_phase === "FAILED" ? "Failed" : "Healthy";
}

function healthChipClass() {
  return state.task.current_phase === "FAILED"
    ? "status-chip status-chip--phase"
    : "status-chip status-chip--healthy";
}

function approvalHeaderText() {
  if (state.task.current_phase === "FAILED") return "Rejected";
  if (state.task.current_phase === "3_HUMAN_IN_THE_LOOP") return "Pending review";
  if (phaseIndex(state.task.current_phase) >= phaseIndex("4_COMPUTE_ROUTING")) return "Approved";
  return "Awaiting prompt";
}

function approvalHeaderClass() {
  if (state.task.current_phase === "FAILED") return "status-chip status-chip--phase";
  if (phaseIndex(state.task.current_phase) >= phaseIndex("4_COMPUTE_ROUTING")) return "status-chip status-chip--healthy";
  return "status-chip status-chip--healthy";
}

function outputStatusLabel() {
  if (state.task.current_phase === "FINISHED") return "Sandbox passing";
  if (state.task.current_phase === "5_SANDBOX_TESTING") return "Sandbox running";
  if (state.task.current_phase === "4_COMPUTE_ROUTING") return "Code generating";
  if (state.task.current_phase === "FAILED") return "Task failed";
  return "Waiting";
}

function outputStatusClass() {
  return state.task.current_phase === "FAILED"
    ? "status-chip status-chip--phase"
    : "status-chip status-chip--healthy";
}

function outputPhaseLabel() {
  if (state.task.current_phase === "FINISHED") return "Finished · 5/5";
  if (state.task.current_phase === "FAILED") return "Failed";
  return `${phaseHeadline(state.task.current_phase)} · ${Math.min(phaseIndex(state.task.current_phase) + 1, 5)}/5`;
}

function iterationProgress() {
  if (!state.task.max_iterations) return 0;
  return (state.task.sandbox_iterations / state.task.max_iterations) * 100;
}

function prBranchLabel() {
  if (!state.task.id) return "Not available";
  return `aegis-${state.task.id.slice(0, 8)}`;
}

function compactTaskId(taskId) {
  if (!taskId) return "Not loaded";
  if (taskId.length <= 18) return taskId;
  return `${taskId.slice(0, 8)}...${taskId.slice(-6)}`;
}

function formatProvider(provider) {
  return provider === "nia" ? "Nia" : "GitHub";
}

function formatTime(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " · just now";
}

function totalDurationLabel() {
  const durationValues = Object.values(state.phaseDurations);
  if (!durationValues.length) return "—";
  return durationValues.join(" · ");
}

function phaseLogEntries() {
  return state.logs
    .filter((entry) => entry.level === "PHASE" || entry.level === "OK" || entry.level === "REVIEW")
    .slice(-6)
    .reverse();
}

function logsStatusTitle() {
  if (!state.task.id) return "No active task";
  if (state.task.current_phase === "FINISHED") return "Finished · 5 of 5";
  if (state.task.current_phase === "FAILED") return "Failed";
  return `${phaseHeadline(state.task.current_phase)} · ${Math.min(phaseIndex(state.task.current_phase) + 1, 5)} of 5`;
}

function eventMix() {
  const last = state.logs.slice(-14);
  const counts = { info: 0, ok: 0, review: 0, error: 0, total: last.length };
  last.forEach((entry) => {
    if (entry.level === "INFO" || entry.level === "PHASE") counts.info += 1;
    else if (entry.level === "OK") counts.ok += 1;
    else if (entry.level === "REVIEW") counts.review += 1;
    else counts.error += 1;
  });
  return counts;
}

function updateMixRow(bar, count, value, total) {
  count.textContent = String(value);
  bar.style.width = `${total ? (value / total) * 100 : 0}%`;
}

function renderPromptDocument(source) {
  if (!source) {
    return `<div class="empty-state">No structured prompt available yet.</div>`;
  }
  const sections = source.split(/\n(?=# )/g);
  return `
    <div class="prompt-frame">
      <h3>Structured System Prompt</h3>
      ${sections.map((section) => {
        const [heading, ...lines] = section.split("\n");
        return `
          <div class="prompt-section">
            <div class="prompt-section-label">${escapeHtml(heading.replace(/^#\s*/, ""))}</div>
            <div class="prompt-section-body">${lines.filter(Boolean).map((line) => {
              if (line.trim().startsWith("-")) {
                return `<div class="prompt-bullet">${escapeHtml(line.trim().replace(/^-+\s*/, ""))}</div>`;
              }
              return `<div>${escapeHtml(line)}</div>`;
            }).join("")}</div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
