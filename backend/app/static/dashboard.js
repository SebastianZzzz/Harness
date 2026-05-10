const state = {
  activeNav: "dashboard",
  searchQuery: "",
  secureMode: true,
  autoRefresh: true,
  approvalStatus: "high",
  editingPrompt: false,
  rangeIndex: 1,
  rangeLabels: ["Last 7 Days", "Last 30 Days", "Last 90 Days"],
  promptId: "PRMP-8824-B",
  promptSections: [
    {
      title: "Role Definition",
      lines: [
        "You are AegisHarness, an agentic compiler responsible for turning product intent into secure repository changes.",
      ],
    },
    {
      title: "Core Objectives",
      lines: [
        "1. Translate natural-language requirements into structured implementation plans.",
        "2. Collect repository context before generating code or running tools.",
        "3. Route execution to the most cost-effective model that satisfies risk and latency constraints.",
      ],
    },
    {
      title: "Constraints & Safety Guardrails",
      lines: [
        "Do NOT modify files outside the declared workspace scope.",
        "Do NOT execute destructive commands without explicit approval and rollback notes.",
        "Prefer narrow command escalation. Avoid broad unrestricted shell access whenever a scoped action is enough.",
        "Do NOT ignore sandbox feedback; fold failed review output back into the next generation step.",
      ],
      flaggedIndex: 2,
    },
    {
      title: "Input Contract",
      lines: [
        "Expect prompt intent, similar repositories, historical bug constraints, and human edits before code generation.",
      ],
    },
    {
      title: "Output Structure",
      lines: [
        "Return a structured execution packet containing the prompt summary, proposed patch, validation plan, and post-run log summary.",
      ],
    },
  ],
  approvalRisks: [
    {
      title: "Loose Escalation Constraint",
      copy: "The prompt allows broad shell escalation language without forcing command-level scope or rollback criteria.",
      tags: ["Line 11", "Compliance: Internal", "High Severity"],
      severity: "high",
    },
    {
      title: "Missing Failure Rollback Step",
      copy: "No explicit instruction tells the agent how to restore the workspace if sandbox validation fails after patch application.",
      tags: ["UX Reliability", "Stage 5", "Medium"],
      severity: "medium",
    },
  ],
  routingMetrics: {
    "Last 7 Days": {
      value: "$11.6k",
      delta: "↗ +8.4% vs previous period",
      bars: [18, 28, 41, 56, 34, 16],
      legend: [
        { label: "Low (Llama 3 8B)", color: "#cec5b8" },
        { label: "Mid (Claude 3.5 Haiku)", color: "#9c9387" },
        { label: "High (GPT-4o)", color: "#3b342d" },
      ],
      dispatch: [
        { name: "Claude 3.5 Sonnet", share: 38, requests: "78k Requests", latency: "Avg Latency: 760ms" },
        { name: "GPT-4o", share: 35, requests: "64k Requests", latency: "Avg Latency: 1.1s" },
        { name: "Llama 3 70B (Local)", share: 27, requests: "52k Requests", latency: "Avg Latency: 290ms" },
      ],
    },
    "Last 30 Days": {
      value: "$42.8k",
      delta: "↗ +14.2% vs previous period",
      bars: [14, 23, 37, 49, 26, 9],
      legend: [
        { label: "Low (Llama 3 8B)", color: "#cec5b8" },
        { label: "Mid (Claude 3.5 Haiku)", color: "#9c9387" },
        { label: "High (GPT-4o)", color: "#3b342d" },
      ],
      dispatch: [
        { name: "Claude 3.5 Sonnet", share: 45, requests: "245k Requests", latency: "Avg Latency: 840ms" },
        { name: "GPT-4o", share: 32, requests: "174k Requests", latency: "Avg Latency: 1.2s" },
        { name: "Llama 3 70B (Local)", share: 23, requests: "125k Requests", latency: "Avg Latency: 320ms" },
      ],
    },
    "Last 90 Days": {
      value: "$119.3k",
      delta: "↗ +19.6% vs previous period",
      bars: [10, 18, 29, 44, 32, 18],
      legend: [
        { label: "Low (Llama 3 8B)", color: "#cec5b8" },
        { label: "Mid (Claude 3.5 Haiku)", color: "#9c9387" },
        { label: "High (GPT-4o)", color: "#3b342d" },
      ],
      dispatch: [
        { name: "Claude 3.5 Sonnet", share: 43, requests: "702k Requests", latency: "Avg Latency: 880ms" },
        { name: "GPT-4o", share: 29, requests: "514k Requests", latency: "Avg Latency: 1.3s" },
        { name: "Llama 3 70B (Local)", share: 28, requests: "468k Requests", latency: "Avg Latency: 340ms" },
      ],
    },
  },
  routingPreview: `import { ClodRouter } from "@aegis/clod-router";

const router = new ClodRouter({
  strategy: "cost-optimized",
  fallbackModel: "gpt-4o",
  guardrails: ["sandbox_review", "policy_constraints", "human_override"],
});

router.route({
  if: ({ complexityScore, tokens }) => complexityScore < 0.30 && tokens < 1000,
  target: "llama-3.1-8b-local",
  reason: "Low complexity, low latency path",
});

router.route({
  if: ({ complexityScore, policyRisk }) => complexityScore < 0.68 && policyRisk < 0.45,
  target: "claude-3.5-sonnet",
  reason: "Balanced throughput with strong reasoning",
});

router.route({
  if: ({ complexityScore, policyRisk, sandboxRetries }) =>
    complexityScore >= 0.68 || policyRisk >= 0.45 || sandboxRetries > 0,
  target: "gpt-4o",
  reason: "Escalate for high-risk or recovery-bound workloads",
});`,
  stages: [
    {
      id: "stage1",
      index: "Stage 1",
      name: "Trynia Intent",
      copy: "Intent parsed with repository context attached.",
      status: "Active",
      progress: 88,
      open: "dashboard",
      icon: "intent",
    },
    {
      id: "stage2",
      index: "Stage 2",
      name: "Greptile Risk",
      copy: "Constraint extraction and policy scan in motion.",
      status: "Processing",
      progress: 62,
      open: "dashboard",
      icon: "shield",
    },
    {
      id: "stage3",
      index: "Stage 3",
      name: "HITL Approval",
      copy: "Waiting for human validation before execution.",
      status: "Pending",
      progress: 18,
      open: "approval",
      icon: "document",
    },
    {
      id: "stage4",
      index: "Stage 4",
      name: "Clod Routing",
      copy: "Routing thresholds idle until approval clears.",
      status: "Waiting",
      progress: 0,
      open: "routing",
      icon: "routing",
    },
    {
      id: "stage5",
      index: "Stage 5",
      name: "Sandbox Healing",
      copy: "TREX container loop queued for generated patch review.",
      status: "Waiting",
      progress: 0,
      open: "logs",
      icon: "clock",
    },
  ],
  timeline: [
    {
      title: "Risk Flagged: Escalation Prompt Drift",
      copy: "Greptile identified an overly broad shell escalation clause in the generated system prompt.",
      tags: ["Stage 2", "Action Required"],
      time: "10:42 AM",
    },
    {
      title: "Intent Parsed Successfully",
      copy: "Trynia aligned the request to repository-aware implementation with 98% confidence.",
      tags: ["Stage 1", "Cleared"],
      time: "10:41 AM",
    },
    {
      title: "Constraint Pack Refreshed",
      copy: "Historical bug signatures and security exclusions were attached to the execution packet.",
      tags: ["Stage 2", "Guardrails"],
      time: "10:38 AM",
    },
    {
      title: "Dynamic Route Updated",
      copy: "Clod pre-warmed the fallback premium cluster after detecting rising sandbox retry probability.",
      tags: ["Stage 4", "Queued"],
      time: "10:35 AM",
    },
  ],
  healingCycles: [
    {
      label: "Cycle 01 / Pass",
      time: "10:42:01 AM",
      copy: "Dependency injection resolved. Minor memory leak detected and patched dynamically.",
    },
    {
      label: "Cycle 02 / Pass",
      time: "10:45:22 AM",
      copy: "Threat deadlock averted. Sandbox state rolled back to checkpoint Alpha for re-execution.",
    },
    {
      label: "Cycle 03 / Active",
      time: "10:48:15 AM",
      copy: "Attempting to sanitize malicious input string bypassing regex filter. Applying heuristic masks.",
    },
  ],
  terminalLines: [
    { tone: "muted", text: "[10:48:10.001] INFO: Initializing sandbox container v4.2.1" },
    { tone: "muted", text: "[10:48:10.045] INFO: Mounting volumes... OK." },
    { tone: "muted", text: "[10:48:11.200] INFO: Establishing network isolation bridge." },
    { tone: "muted", text: "[10:48:12.553] WARN: Deprecated flag 'allow_unsafe_eval' detected in config. Ignored." },
    { tone: "", text: "[10:48:14.102] EXEC: Invoking user payload routine." },
    { tone: "", text: "  >> Analyzing AST stream..." },
    { tone: "", text: "  >> Identifying potential deep-eval nodes..." },
    { tone: "", text: "  >> Sandboxing memory allocations (limit: 512MB)" },
    { tone: "alert", text: "[10:48:15.001] ALERT: Anomalous string pattern detected. Possible SQLi heuristic match." },
    { tone: "alert", text: "[10:48:15.050] TRIG: Initiating Self-Healing Cycle 03." },
    { tone: "muted", text: "[10:48:15.100] INFO: Halting execution. Snapshotting state to /tmp/trx_snap_03." },
    { tone: "", text: "  >> Applying masking filter to payload line 42." },
    { tone: "", text: "  >> Recompiling..." },
    { tone: "", text: "[10:48:16.882] AWAIT: Verifying sanitized payload against rule engine..." },
  ],
};

const els = {};
let refreshTimer;

document.addEventListener("DOMContentLoaded", () => {
  captureElements();
  bindEvents();
  render();
  refreshTimer = window.setInterval(tickAutoRefresh, 3200);
});

function captureElements() {
  els.views = {
    dashboard: document.getElementById("view-dashboard"),
    workflows: document.getElementById("view-workflows"),
    logs: document.getElementById("view-logs"),
  };
  els.search = document.getElementById("global-search");
  els.stageCards = document.getElementById("stage-cards");
  els.timelineFeed = document.getElementById("timeline-feed");
  els.promptSurface = document.getElementById("prompt-surface");
  els.riskList = document.getElementById("risk-list");
  els.promptId = document.getElementById("prompt-id-badge");
  els.approvalRiskPill = document.getElementById("approval-risk-pill");
  els.efficiencyValue = document.getElementById("efficiency-value");
  els.efficiencyDelta = document.getElementById("efficiency-delta");
  els.dispatchList = document.getElementById("dispatch-list");
  els.chart = document.getElementById("complexity-chart");
  els.legend = document.getElementById("complexity-legend");
  els.routingCode = document.getElementById("routing-code");
  els.rangeButton = document.getElementById("cycle-range");
  els.healingList = document.getElementById("healing-list");
  els.terminalOutput = document.getElementById("terminal-output");
  els.systemLoadValue = document.getElementById("system-load-value");
  els.systemLoadDelta = document.getElementById("system-load-delta");
  els.blockedRisksValue = document.getElementById("blocked-risks-value");
  els.blockedRisksDelta = document.getElementById("blocked-risks-delta");
  els.secureToggle = document.getElementById("toggle-secure-mode");
  els.refreshToggle = document.getElementById("toggle-auto-refresh");
  els.sandboxState = document.getElementById("sandbox-state");
  els.sandboxSession = document.getElementById("sandbox-session");
  els.sandboxEnv = document.getElementById("sandbox-env");
  els.sandboxUptime = document.getElementById("sandbox-uptime");
  els.sandboxOrb = document.getElementById("sandbox-orb");
  els.scanInjection = document.getElementById("scan-injection");
  els.scanAuth = document.getElementById("scan-auth");
  els.scanExfiltration = document.getElementById("scan-exfiltration");
}

function bindEvents() {
  document.querySelectorAll("[data-nav-target]").forEach((button) => {
    button.addEventListener("click", () => {
      navigate(button.dataset.navTarget);
    });
  });

  els.search.addEventListener("input", (event) => {
    state.searchQuery = event.target.value.trim().toLowerCase();
    render();
  });

  document.getElementById("edit-prompt").addEventListener("click", togglePromptEditing);
  document.getElementById("approve-prompt").addEventListener("click", approvePrompt);
  document.getElementById("reject-prompt").addEventListener("click", rejectPrompt);
  document.getElementById("bypass-hitl").addEventListener("click", bypassApproval);
  document.getElementById("force-sandbox").addEventListener("click", forceSandboxRefresh);
  document.getElementById("cycle-range").addEventListener("click", cycleRange);
  document.getElementById("copy-routing-code").addEventListener("click", copyRoutingCode);
  document.getElementById("toggle-secure-mode").addEventListener("click", toggleSecureMode);
  document.getElementById("toggle-auto-refresh").addEventListener("click", toggleAutoRefresh);
  document.getElementById("export-dashboard-log").addEventListener("click", exportDashboardLog);
  document.getElementById("export-routing-report").addEventListener("click", exportRoutingReport);
  document.getElementById("export-scan-report").addEventListener("click", exportScanReport);
}

function navigate(target) {
  state.activeNav = target;
  render();
}

function render() {
  renderNavState();
  renderStages();
  renderTimeline();
  renderApproval();
  renderRouting();
  renderLogs();
}

function renderNavState() {
  const visibleView = state.activeNav === "approval" || state.activeNav === "routing" ? "workflows" : state.activeNav;
  Object.entries(els.views).forEach(([key, node]) => {
    node.classList.toggle("is-active", key === visibleView);
  });

  document.querySelectorAll(".workflow-panel").forEach((node) => {
    const active = node.id === (state.activeNav === "routing" ? "workflow-routing" : "workflow-approval");
    node.classList.toggle("is-active", active);
  });

  document.querySelectorAll(".rail-action").forEach((button) => {
    const navTarget = button.dataset.navTarget;
    const active = navTarget && navTarget === state.activeNav;
    button.classList.toggle("is-active", active);
  });

  els.search.placeholder =
    state.activeNav === "logs"
      ? "Search logs..."
      : state.activeNav === "approval" || state.activeNav === "routing"
        ? "Search workflows..."
        : "Search insights...";
}

function renderStages() {
  els.stageCards.innerHTML = state.stages
    .map((stage) => {
      const clickable = stage.open === "approval" || stage.open === "routing" || stage.open === "logs";
      const buttonAttrs = clickable
        ? `data-stage-open="${stage.open}" class="stage-card is-clickable"`
        : `class="stage-card"`;
      return `
        <button type="button" ${buttonAttrs}>
          <div class="stage-card-top">
            <span class="stage-icon">${stageIcon(stage.icon)}</span>
            <span class="status-pill">${escapeHtml(stage.status)}</span>
          </div>
          <div class="stage-index">${escapeHtml(stage.index)}</div>
          <div class="stage-name">${escapeHtml(stage.name)}</div>
          <div class="stage-copy">${escapeHtml(stage.copy)}</div>
          <div class="stage-progress"><span style="width:${stage.progress}%"></span></div>
        </button>
      `;
    })
    .join("");

  els.stageCards.querySelectorAll("[data-stage-open]").forEach((button) => {
    button.addEventListener("click", () => {
      navigate(button.dataset.stageOpen);
    });
  });
}

function renderTimeline() {
  const items = filterItems(state.timeline, (item) => [item.title, item.copy, item.tags.join(" "), item.time]);
  els.timelineFeed.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <article class="timeline-item">
              <span class="timeline-dot"></span>
              <div class="timeline-body">
                <div class="timeline-title">${escapeHtml(item.title)}</div>
                <p class="timeline-copy">${escapeHtml(item.copy)}</p>
                <div class="timeline-tags">
                  ${item.tags.map((tag) => `<span class="event-badge">${escapeHtml(tag)}</span>`).join("")}
                </div>
              </div>
              <div class="timeline-time">${escapeHtml(item.time)}</div>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">No stream events match the current search.</div>`;
}

function renderApproval() {
  els.promptId.textContent = state.promptId;
  els.approvalRiskPill.textContent =
    state.approvalStatus === "approved"
      ? "Approved"
      : state.approvalStatus === "rejected"
        ? "Rejected"
        : "High Risk";
  els.approvalRiskPill.className =
    state.approvalStatus === "approved"
      ? "severity-pill severity-pill--approved"
      : state.approvalStatus === "rejected"
        ? "severity-pill severity-pill--rejected"
        : "severity-pill severity-pill--high";

  if (state.editingPrompt) {
    els.promptSurface.innerHTML = `<textarea id="prompt-editor" class="prompt-editor">${escapeHtml(promptTextFromSections())}</textarea>`;
  } else {
    const filteredSections = state.promptSections
      .map((section) => ({
        ...section,
        lines: section.lines.filter((line) => matchesQuery(`${section.title} ${line}`)),
      }))
      .filter((section) => section.lines.length);

    els.promptSurface.innerHTML = filteredSections.length
      ? `<div class="prompt-reading">
          ${filteredSections
            .map(
              (section) => `
                <section>
                  <h3 class="prompt-section-title"># ${escapeHtml(section.title)}</h3>
                  <ul class="prompt-lines">
                    ${section.lines
                      .map((line, index) => {
                        const originalIndex = state.promptSections.find((entry) => entry.title === section.title).lines.indexOf(line);
                        const flagged = originalIndex === section.flaggedIndex ? "is-flagged" : "";
                        return `<li class="prompt-line ${flagged}">${escapeHtml(line)}</li>`;
                      })
                      .join("")}
                  </ul>
                </section>
              `,
            )
            .join("")}
        </div>`
      : `<div class="empty-state">No prompt clauses match the current search.</div>`;
  }

  const risks = filterItems(state.approvalRisks, (item) => [item.title, item.copy, item.tags.join(" ")]);
  els.riskList.innerHTML = risks.length
    ? risks
        .map(
          (risk) => `
            <article class="risk-item ${risk.severity === "high" ? "is-high" : ""}">
              <div class="risk-header">
                <div class="risk-title">${escapeHtml(risk.title)}</div>
                <span class="status-pill">${escapeHtml(risk.severity === "high" ? "Flagged" : "Advisory")}</span>
              </div>
              <div class="risk-copy">${escapeHtml(risk.copy)}</div>
              <div class="risk-foot">
                ${risk.tags.map((tag) => `<span class="risk-chip">${escapeHtml(tag)}</span>`).join("")}
              </div>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">No approval risks match the current search.</div>`;
}

function renderRouting() {
  const range = state.rangeLabels[state.rangeIndex];
  const metrics = state.routingMetrics[range];
  els.rangeButton.textContent = range;
  els.efficiencyValue.textContent = metrics.value;
  els.efficiencyDelta.textContent = metrics.delta;

  const dispatchItems = filterItems(metrics.dispatch, (item) => [item.name, item.requests, item.latency]);
  els.dispatchList.innerHTML = dispatchItems
    .map(
      (item) => `
        <article class="dispatch-item">
          <div class="dispatch-meta">
            <div class="dispatch-name">${escapeHtml(item.name)}</div>
            <div class="progress-track"><span style="width:${item.share}%"></span></div>
            <div class="dispatch-stats">
              <span>${escapeHtml(item.requests)}</span>
              <span>${escapeHtml(item.latency)}</span>
            </div>
          </div>
          <div class="dispatch-usage">${item.share}%</div>
        </article>
      `,
    )
    .join("");

  els.chart.innerHTML = metrics.bars
    .map((value, index) => {
      const color = index < 2 ? "#d1c8bb" : index < 4 ? "#9f968a" : "#3c342d";
      return `<div class="complexity-bar"><span style="--bar-height:${value}%;--bar-color:${color}"></span></div>`;
    })
    .join("");

  els.legend.innerHTML = metrics.legend
    .map(
      (item) => `
        <span class="legend-item" style="color:${item.color}">
          <span class="legend-dot"></span>${escapeHtml(item.label)}
        </span>
      `,
    )
    .join("");

  els.routingCode.textContent = matchesQuery(state.routingPreview) || !state.searchQuery ? state.routingPreview : "// No routing preview lines match the current search.";
}

function renderLogs() {
  const injection = state.secureMode ? 0 : 1;
  const auth = state.secureMode ? 0 : 1;
  const exfiltration = state.secureMode ? 1 : 3;

  els.secureToggle.classList.toggle("is-active", state.secureMode);
  els.refreshToggle.classList.toggle("is-active", state.autoRefresh);
  els.secureToggle.setAttribute("aria-pressed", String(state.secureMode));
  els.refreshToggle.setAttribute("aria-pressed", String(state.autoRefresh));
  els.sandboxState.textContent = state.secureMode ? "Active Monitoring" : "Review Mode";
  els.sandboxSession.textContent = state.secureMode ? "TRX-992-A" : "TRX-992-B";
  els.sandboxEnv.textContent = state.secureMode ? "Isolated Container 04" : "Diagnostic Container";
  els.sandboxUptime.textContent = state.secureMode ? "02:14:45" : "00:36:11";
  els.sandboxOrb.style.borderColor = state.secureMode ? "rgba(47,41,35,0.2)" : "rgba(200,81,70,0.28)";
  els.scanInjection.textContent = String(injection);
  els.scanAuth.textContent = String(auth);
  els.scanExfiltration.textContent = String(exfiltration);

  const cycles = filterItems(state.healingCycles, (item) => [item.label, item.copy, item.time]);
  els.healingList.innerHTML = cycles.length
    ? cycles
        .map(
          (item) => `
            <article class="cycle-item">
              <div class="cycle-head">
                <span class="cycle-label">${escapeHtml(item.label)}</span>
                <span class="cycle-time">${escapeHtml(item.time)}</span>
              </div>
              <p class="cycle-copy">${escapeHtml(item.copy)}</p>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">No healing cycle entries match the current search.</div>`;

  const lines = state.terminalLines.filter((line) => matchesQuery(line.text));
  els.terminalOutput.innerHTML = lines.length
    ? lines
        .map((line) => `<div class="terminal-line ${line.tone ? `is-${line.tone}` : ""}">${escapeHtml(line.text)}</div>`)
        .join("")
    : `<div class="empty-state">No terminal lines match the current search.</div>`;

  const systemLoad = state.approvalStatus === "approved" ? "31.2%" : "24.8%";
  const blockedRisks = state.approvalStatus === "approved" ? "143" : state.approvalStatus === "rejected" ? "148" : "142";
  els.systemLoadValue.textContent = systemLoad;
  els.systemLoadDelta.textContent = state.approvalStatus === "approved" ? "↗ +4.1% during execution ramp" : "↘ -2.4% from last hour";
  els.blockedRisksValue.textContent = blockedRisks;
  els.blockedRisksDelta.textContent = state.approvalStatus === "rejected" ? "↗ +18 since yesterday" : "↗ +12 since yesterday";
}

function togglePromptEditing() {
  if (state.editingPrompt) {
    const editor = document.getElementById("prompt-editor");
    if (editor) {
      state.promptSections = parsePrompt(editor.value);
    }
  }
  state.editingPrompt = !state.editingPrompt;
  document.getElementById("edit-prompt").textContent = state.editingPrompt ? "Save Prompt" : "Edit Prompt";
  renderApproval();
}

function approvePrompt() {
  if (state.editingPrompt) {
    togglePromptEditing();
  }
  state.approvalStatus = "approved";
  patchStage("stage1", { status: "Complete", progress: 100, copy: "Intent packet approved and frozen for execution." });
  patchStage("stage2", { status: "Complete", progress: 100, copy: "Constraint bundle sealed for generation." });
  patchStage("stage3", { status: "Approved", progress: 100, copy: "Human reviewer cleared execution packet." });
  patchStage("stage4", { status: "Active", progress: 54, copy: "Clod routing dispatching workload to balanced tier." });
  patchStage("stage5", { status: "Queued", progress: 22, copy: "Sandbox container primed for generated patch review." });
  state.timeline.unshift({
    title: "Approval Granted",
    copy: "Operator approved the constrained prompt and released compute routing.",
    tags: ["Stage 3", "Approved"],
    time: "10:46 AM",
  });
  state.terminalLines.push({ tone: "", text: "[10:49:03.120] EXEC: Approval received. Dispatching generation request to Clod." });
  navigate("routing");
}

function rejectPrompt() {
  if (state.editingPrompt) {
    togglePromptEditing();
  }
  state.approvalStatus = "rejected";
  patchStage("stage3", { status: "Rejected", progress: 100, copy: "Execution halted pending prompt rewrite." });
  patchStage("stage4", { status: "Blocked", progress: 0, copy: "Routing paused until revised approval." });
  patchStage("stage5", { status: "Blocked", progress: 0, copy: "Sandbox queue released without execution." });
  state.timeline.unshift({
    title: "Approval Rejected",
    copy: "Reviewer returned the system prompt for stricter escalation and rollback guidance.",
    tags: ["Stage 3", "Blocked"],
    time: "10:46 AM",
  });
  state.terminalLines.push({ tone: "alert", text: "[10:49:03.120] ABORT: Approval rejected. Sandbox execution cancelled." });
  navigate("dashboard");
}

function bypassApproval() {
  state.approvalStatus = "approved";
  patchStage("stage3", { status: "Overridden", progress: 100, copy: "Quick override bypassed HITL gate for internal dry-run." });
  patchStage("stage4", { status: "Active", progress: 46, copy: "Routing thresholds executing under operator override." });
  patchStage("stage5", { status: "Queued", progress: 12, copy: "Sandbox refresh requested from override panel." });
  state.timeline.unshift({
    title: "HITL Queue Bypassed",
    copy: "Operator bypassed manual approval for an internal dry-run environment.",
    tags: ["Stage 3", "Override"],
    time: "10:47 AM",
  });
  render();
}

function forceSandboxRefresh() {
  state.terminalLines.push({ tone: "", text: "[10:49:44.221] INFO: Manual sandbox refresh requested by operator." });
  state.terminalLines.push({ tone: "", text: "[10:49:44.902] INFO: Provisioning fresh recovery snapshot." });
  state.timeline.unshift({
    title: "Sandbox Refresh Triggered",
    copy: "Quick override requested a fresh recovery snapshot for the active sandbox container.",
    tags: ["Stage 5", "Refresh"],
    time: "10:49 AM",
  });
  navigate("logs");
}

function cycleRange() {
  state.rangeIndex = (state.rangeIndex + 1) % state.rangeLabels.length;
  renderRouting();
}

async function copyRoutingCode() {
  try {
    await navigator.clipboard.writeText(state.routingPreview);
  } catch {
    // no-op fallback for preview environments
  }
}

function toggleSecureMode() {
  state.secureMode = !state.secureMode;
  renderLogs();
}

function toggleAutoRefresh() {
  state.autoRefresh = !state.autoRefresh;
  renderLogs();
}

function exportDashboardLog() {
  const content = state.timeline.map((item) => `${item.time} | ${item.title}\n${item.copy}\n[${item.tags.join(", ")}]`).join("\n\n");
  downloadFile("aegis-dashboard-log.txt", content, "text/plain");
}

function exportRoutingReport() {
  const range = state.rangeLabels[state.rangeIndex];
  const report = {
    range,
    metrics: state.routingMetrics[range],
    preview: state.routingPreview,
  };
  downloadFile("routing-report.json", JSON.stringify(report, null, 2), "application/json");
}

function exportScanReport() {
  const report = {
    secureMode: state.secureMode,
    cycles: state.healingCycles,
    terminalLines: state.terminalLines.map((line) => line.text),
  };
  downloadFile("sandbox-scan-report.json", JSON.stringify(report, null, 2), "application/json");
}

function tickAutoRefresh() {
  if (!state.autoRefresh) {
    return;
  }
  const pulse = [
    "[10:49:51.104] INFO: Re-validating policy masks against latest guardrail bundle.",
    "[10:49:54.338] INFO: Clod latency probe stable across premium region.",
    "[10:49:58.707] INFO: TREX heartbeat acknowledged by container supervisor.",
  ];
  const next = pulse[Math.floor(Math.random() * pulse.length)];
  state.terminalLines = [...state.terminalLines.slice(-15), { tone: "muted", text: next }];
  renderLogs();
}

function promptTextFromSections() {
  return state.promptSections
    .map((section) => `# ${section.title}\n${section.lines.join("\n")}`)
    .join("\n\n");
}

function parsePrompt(source) {
  return source
    .split(/\n(?=# )/g)
    .map((block) => {
      const [heading, ...lines] = block.split("\n");
      return {
        title: heading.replace(/^#\s*/, "").trim() || "Untitled Section",
        lines: lines.filter(Boolean),
      };
    })
    .filter((section) => section.lines.length);
}

function patchStage(stageId, patch) {
  state.stages = state.stages.map((stage) => (stage.id === stageId ? { ...stage, ...patch } : stage));
}

function filterItems(items, pickFields) {
  if (!state.searchQuery) {
    return items;
  }
  return items.filter((item) => pickFields(item).some((field) => matchesQuery(field)));
}

function matchesQuery(value) {
  if (!state.searchQuery) {
    return true;
  }
  return String(value).toLowerCase().includes(state.searchQuery);
}

function downloadFile(name, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function stageIcon(type) {
  const icons = {
    intent: `<svg viewBox="0 0 24 24" class="icon"><circle cx="12" cy="12" r="7"></circle><path d="M12 12 15.2 9.2"></path><path d="M12 8v4l2 2"></path></svg>`,
    shield: `<svg viewBox="0 0 24 24" class="icon"><path d="M12 3 5 6v6c0 4.6 2.9 7.8 7 9 4.1-1.2 7-4.4 7-9V6l-7-3Z"></path></svg>`,
    document: `<svg viewBox="0 0 24 24" class="icon"><rect x="6" y="4" width="12" height="16" rx="2"></rect><path d="M9 8h6"></path><path d="M9 12h6"></path><path d="M9 16h4"></path></svg>`,
    routing: `<svg viewBox="0 0 24 24" class="icon"><path d="M7 6h10"></path><path d="M7 12h6"></path><path d="M7 18h3"></path><circle cx="18" cy="6" r="2"></circle><circle cx="15" cy="12" r="2"></circle><circle cx="12" cy="18" r="2"></circle></svg>`,
    clock: `<svg viewBox="0 0 24 24" class="icon"><circle cx="12" cy="12" r="8"></circle><path d="M12 8v5l3 2"></path></svg>`,
  };
  return icons[type] || icons.intent;
}
