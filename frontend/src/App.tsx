import { useEffect, useMemo, useRef, useState } from "react";
import {
  approveTask,
  initTask,
  setTaskConfig,
  startTask,
  fetchHealth,
  loadTask,
  rejectTask,
  listTasks,
  deleteTask,
  restartSystem,
  type BackendTask,
} from "./api";

type ViewKey = "workflow" | "approval" | "output" | "logs";

type LogLevel = "info" | "ok" | "review" | "err";

type LogEntry = {
  time: string;
  level: string;
  tone: LogLevel;
  message: string;
};

type StreamEntry = {
  title: string;
  detail: string;
};

type PhaseMeta = {
  key: string;
  step: string;
  title: string;
  desc: string;
  view: ViewKey;
};

const STORAGE_KEY = "aegis.task.id";
const GITHUB_TOKEN_KEY = "aegis.github.token";
const TARGET_REPO_KEY = "aegis.target.repo";
const TARGET_REPO = "Harness";

const PHASES: PhaseMeta[] = [
  { key: "1_INTENT_PARSING", step: "01", title: "Intake", desc: "Parse the request into a structured prompt skeleton.", view: "workflow" },
  { key: "2_PRECHECK_GREPTILE", step: "02", title: "Context fetch", desc: "Search for similar repos and extract constraints.", view: "workflow" },
  { key: "3_HUMAN_IN_THE_LOOP", step: "03", title: "Approval", desc: "Reviewer confirms the structured prompt is safe.", view: "approval" },
  { key: "4_COMPUTE_ROUTING", step: "04", title: "Code gen", desc: "Model writes the implementation against constraints.", view: "output" },
  { key: "5_SANDBOX_TESTING", step: "05", title: "Sandbox", desc: "Run, review, retry up to 3× until checks pass.", view: "logs" },
  { key: "6_REWRITING", step: "06", title: "Self-repair", desc: "AI fixes bugs found during sandbox review.", view: "output" },
];

const EMPTY_TASK: BackendTask = {
  id: "",
  original_prompt: "",
  structured_prompt: "",
  bug_list_constraints: [],
  current_phase: "1_INTENT_PARSING",
  search_provider: "github",
  difficulty_score: null,
  selected_model: null,
  generated_code: null,
  sandbox_iterations: 0,
  max_iterations: 3,
  created_at: "",
  updated_at: "",
};

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function WorkflowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="6" height="6" rx="1" />
      <rect x="15" y="15" width="6" height="6" rx="1" />
      <path d="M9 6h6a3 3 0 0 1 3 3v6" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
      <path d="M14 3v6h6" />
      <path d="M8 13h8M8 17h5" />
    </svg>
  );
}

function SlidersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="6" x2="14" y2="6" />
      <line x1="18" y1="6" x2="20" y2="6" />
      <circle cx="16" cy="6" r="2" />
      <line x1="4" y1="12" x2="8" y2="12" />
      <line x1="12" y1="12" x2="20" y2="12" />
      <circle cx="10" cy="12" r="2" />
      <line x1="4" y1="18" x2="14" y2="18" />
      <line x1="18" y1="18" x2="20" y2="18" />
      <circle cx="16" cy="18" r="2" />
    </svg>
  );
}

function LogsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16v16H4z" />
      <path d="M8 9h8M8 13h8M8 17h5" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
      <path d="M3 21v-5h5" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12l5 5L20 7" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  );
}

function DiffIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="6" cy="6" r="2" />
      <circle cx="18" cy="18" r="2" />
      <path d="M6 8v8M18 16V8a4 4 0 0 0-4-4h-2M18 8h-2M10 4 8 6l2 2" />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 19c-4 1.5-4-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12 12 0 0 0-6 0C7.7 2.8 6.6 3.1 6.6 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 5.2 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21" />
    </svg>
  );
}

function App() {
  const [view, setView] = useState<ViewKey>("workflow");
  const [task, setTask] = useState<BackendTask>(EMPTY_TASK);
  const [request, setRequest] = useState("");
  const [searchProvider, setSearchProvider] = useState("github");
  const [githubToken, setGithubToken] = useState("");
  const [targetRepo, setTargetRepo] = useState("");
  const [taskInput, setTaskInput] = useState("");
  const [backendConnected, setBackendConnected] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [tailFollow, setTailFollow] = useState(true);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [history, setHistory] = useState<BackendTask[]>([]);
  const [prUrl, setPrUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const terminalRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void refreshHealth();
    void fetchHistory();
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setTaskInput(stored);
      void handleLoadTask(stored, true);
    }
    const storedToken = localStorage.getItem(GITHUB_TOKEN_KEY);
    if (storedToken) setGithubToken(storedToken);
    const storedRepo = localStorage.getItem(TARGET_REPO_KEY);
    if (storedRepo) setTargetRepo(storedRepo);
  }, []);

  useEffect(() => {
    if (!autoRefresh || !task.id) {
      return;
    }
    const timer = window.setInterval(() => {
      void handleLoadTask(task.id, true);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, task.id]);

  useEffect(() => {
    if (!task.id) {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/tasks/${task.id}`);

    socket.addEventListener("open", () => {
      pushLog("INFO", "WS connected");
    });

    socket.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          type: "system" | "log" | "state_change";
          message?: string;
          phase?: string;
          data?: Record<string, unknown>;
        };

        if (payload.type === "system" && payload.message) {
          pushLog("INFO", payload.message);
        }

        if (payload.type === "log" && payload.message) {
          pushLog(inferLevel(payload.message), payload.message);
          const match = payload.message.match(/https:\/\/github\.com\/[^\s]+/);
          if (match) {
            setPrUrl(match[0]);
          }
        }

        if (payload.type === "state_change" && payload.phase) {
          setTask((current) => ({
            ...current,
            current_phase: payload.phase!,
            selected_model: typeof payload.data?.selected_model === "string" ? payload.data.selected_model : current.selected_model,
            generated_code: typeof payload.data?.code === "string" ? payload.data.code : current.generated_code,
            updated_at: new Date().toISOString(),
          }));
          pushLog("PHASE", `Task advanced to ${phaseHeadline(payload.phase)}`);
        }
      } catch {
        pushLog("ERR", "Failed to parse socket payload");
      }
    });

    socket.addEventListener("close", () => {
      pushLog("INFO", "Task log stream disconnected");
    });

    return () => {
      socket.close();
    };
  }, [task.id]);

  useEffect(() => {
    if (!tailFollow || !terminalRef.current) {
      return;
    }
    terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [logs, tailFollow]);

  const activeIndex = useMemo(() => phaseIndex(task.current_phase), [task.current_phase]);
  const eventMix = useMemo(() => {
    const last = logs.slice(-14);
    const counts = { info: 0, ok: 0, review: 0, err: 0, total: last.length || 1 };
    last.forEach((log) => {
      if (log.tone === "info") counts.info += 1;
      else if (log.tone === "ok") counts.ok += 1;
      else if (log.tone === "review") counts.review += 1;
      else counts.err += 1;
    });
    return counts;
  }, [logs]);

  const phaseLog = useMemo(() => logs.filter((log) => ["PHASE", "OK", "REVIEW"].includes(log.level)).slice(-4), [logs]);

  async function refreshHealth() {
    try {
      const health = await fetchHealth();
      setBackendConnected(health.status === "healthy");
    } catch {
      setBackendConnected(false);
    }
  }

  async function handleCreateTask() {
    const trimmed = request.trim();
    if (!trimmed || loading) return;
    
    if (!githubToken || !targetRepo) {
      alert("Please provide a GitHub Token and Target Repository.");
      return;
    }
    
    setLoading(true);
    try {
      pushLog("INFO", "Initializing task structure...");
      const initialTask = await initTask();
      const taskId = initialTask.id;

      pushLog("INFO", "Saving GitHub credentials...");
      await setTaskConfig(taskId, githubToken, targetRepo);

      pushLog("INFO", "Starting intent parsing...");
      const started = await startTask(taskId, trimmed, searchProvider);
      
      setTask(started);
      setTaskInput(started.id);
      localStorage.setItem(STORAGE_KEY, started.id);
      setBackendConnected(true);
      setView("workflow");
      pushLog("INFO", `Task ${started.id} started successfully`);
    } catch (error) {
      pushLog("ERR", error instanceof Error ? error.message : "Task creation failed");
    } finally {
      setLoading(false);
      void fetchHistory();
    }
  }

  async function fetchHistory() {
    try {
      const tasks = await listTasks();
      setHistory(tasks.slice(0, 15)); // Only show last 15
    } catch {
      // silent
    }
  }

  async function handleDeleteTask(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm("Delete this task from history?")) return;
    try {
      await deleteTask(id);
      if (task.id === id) {
        setTask(EMPTY_TASK);
        localStorage.removeItem(STORAGE_KEY);
      }
      void fetchHistory();
    } catch (err) {
      alert("Failed to delete task.");
    }
  }

  async function handleLoadTask(input = taskInput, silent = false) {
    const trimmed = input.trim();
    if (!trimmed) return;
    try {
      const loaded = await loadTask(trimmed);
      setTask(loaded);
      setTaskInput(loaded.id);
      setRequest(loaded.original_prompt || "");
      setSearchProvider(loaded.search_provider || "github");
      localStorage.setItem(STORAGE_KEY, loaded.id);
      setBackendConnected(true);
      if (!silent) {
        pushLog("INFO", `Loaded task ${loaded.id}`);
      }
    } catch (error) {
      pushLog("ERR", error instanceof Error ? error.message : "Task load failed");
    }
  }

  function handleNewTask() {
    if (task.id && !window.confirm("Start a new task? Any unsaved changes will be lost.")) return;
    setTask(EMPTY_TASK);
    setTaskInput("");
    setRequest("");
    setLogs([]);
    setPrUrl("");
    localStorage.removeItem(STORAGE_KEY);
    setView("workflow");
    pushLog("INFO", "Ready for a new task");
  }

  async function handleApprove() {
    if (!task.id || loading) return;
    setLoading(true);
    try {
      const editedPrompt = (document.getElementById("approval-editor") as HTMLTextAreaElement | null)?.value ?? task.structured_prompt ?? "";
      const approved = await approveTask(task.id, editedPrompt);
      setTask(approved);
      setView("output");
      pushLog("OK", "Approval granted");
    } catch (error) {
      pushLog("ERR", error instanceof Error ? error.message : "Approval failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleReject() {
    if (!task.id || loading) return;
    setLoading(true);
    try {
      const rejected = await rejectTask(task.id);
      setTask(rejected);
      setView("workflow");
      pushLog("REVIEW", "Task rejected");
    } catch (error) {
      pushLog("ERR", error instanceof Error ? error.message : "Reject failed");
    } finally {
      setLoading(false);
    }
  }

  function pushLog(level: string, message: string) {
    const timestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    setLogs((current) => [...current, { time: timestamp, level, tone: levelTone(level), message }].slice(-200));
  }

  function copyTaskId() {
    if (task.id) void navigator.clipboard.writeText(task.id);
  }

  function copyCode() {
    if (task.generated_code) void navigator.clipboard.writeText(task.generated_code);
  }

  function openPr() {
    if (prUrl) window.open(prUrl, "_blank", "noopener,noreferrer");
  }

  function openDiff() {
    if (prUrl) window.open(`${prUrl}/files`, "_blank", "noopener,noreferrer");
  }

  function exportLog() {
    const text = logs.map((log) => `[${log.time}] ${log.level} ${log.message}`).join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "task-execution.log";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function handleRestartSystem() {
    if (!window.confirm("Are you sure you want to RESTART the backend process? \n\nThis will terminate current workers, clear local cache, and reload the server.")) {
      return;
    }
    try {
      pushLog("REVIEW", "🔄 Sending restart command and WIPING ALL DATA...");
      // Total Wipe: Clear everything from local storage
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(GITHUB_TOKEN_KEY);
      localStorage.removeItem(TARGET_REPO_KEY);
      
      await restartSystem();
      pushLog("OK", "Signal sent. Waiting for reload...");
      // Refresh after a delay to wait for reload
      setTimeout(() => window.location.reload(), 1500);
    } catch (err) {
      pushLog("ERR", "Restart signal failed to reach backend.");
    }
  }

  return (
    <main className="browser">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><ShieldIcon /></div>
          <div>
            <div className="brand-name">Aegis</div>
            <div className="brand-sub">Harness · v0.4</div>
          </div>
        </div>

        <div className="nav-group">
          <div className="nav-label">Pipeline</div>
          <button className={`nav-item${view === "workflow" ? " active" : ""}`} onClick={() => setView("workflow")}><WorkflowIcon /><span>Workflow</span><span className="badge">{task.id ? "1" : "0"}</span></button>
          <button className={`nav-item${view === "approval" ? " active" : ""}`} onClick={() => setView("approval")}><DocIcon /><span>Approval</span></button>
          <button className={`nav-item${view === "output" ? " active" : ""}`} onClick={() => setView("output")}><SlidersIcon /><span>Output</span></button>
          <button className={`nav-item${view === "logs" ? " active" : ""}`} onClick={() => setView("logs")}><LogsIcon /><span>Logs</span><span className="badge">{task.id ? "live" : "idle"}</span></button>
        </div>

        <div className="nav-group history-group">
          <div className="nav-label">History</div>
          <div className="history-list">
            {history.length > 0 ? history.map((item) => (
              <div key={item.id} className={`history-item ${task.id === item.id ? "active" : ""}`} onClick={() => void handleLoadTask(item.id)}>
                <div className="history-info">
                  <div className="history-prompt">{item.original_prompt || "Untitled Task"}</div>
                  <div className="history-meta">{compactTaskId(item.id)} · {new Date(item.created_at).toLocaleDateString()}</div>
                </div>
                <button className="history-del" onClick={(e) => void handleDeleteTask(item.id, e)} title="Delete task"><TrashIcon /></button>
              </div>
            )) : <div className="helper" style={{ padding: "0 12px" }}>No previous tasks.</div>}
          </div>
        </div>
      </aside>

      <div className="main">
        <div className="topbar">
          <div className="taskpill">
            <span className="pill-label">Task</span>
            <input className="pill-input" value={taskInput} onChange={(event) => setTaskInput(event.target.value)} placeholder="Load task id" />
            <button className="pill-copy" onClick={copyTaskId}><CopyIcon /></button>
          </div>
          <button className="btn" onClick={() => void handleLoadTask(task.id || taskInput, true)}><RefreshIcon /> Refresh</button>
          <button className="btn danger" onClick={handleRestartSystem}><RefreshIcon /> Restart system</button>
          <button className="btn primary" onClick={handleNewTask}><PlusIcon /> New task</button>
          <div className="spacer" />
          <div className="live-chip"><span className="dot" style={{ background: backendConnected ? "var(--ok)" : "var(--danger)" }} /> {backendConnected ? "Backend connected" : "Backend unavailable"}</div>
        </div>

        <section className={`view ${view === "workflow" ? "active" : ""}`}>
          <PageHeader
            crumbs={["Pipeline", "Workflow"]}
            title="Workflow state machine"
            desc="Create a task, watch the five-phase pipeline run, and monitor approval, code generation, and sandbox review as they progress."
            aside={<span className={`statuspill ${phasePillClass(task.current_phase)}`}>{phaseHeadline(task.current_phase)} · {phaseStatusLabel(task.current_phase)}</span>}
          />
          <div className="workspace">
            <div className="wf-grid">
              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="eyebrow">Step 01</div>
                    <h3>Create task</h3>
                  </div>
                  <span className="statuspill neutral">Phase 1-2 auto-start</span>
                </div>
                <div className="card-body vstack-16">
                  <div className="field">
                    <span className="field-label">Request</span>
                    <textarea className="input" rows={4} value={request} onChange={(event) => setRequest(event.target.value)} />
                    <span className="helper">Plain-language description. The planner expands it into a structured prompt with constraints.</span>
                  </div>
                  <div className="wf-two">
                    <div className="field">
                      <span className="field-label">Search provider</span>
                      <div className="select-wrap">
                        <select className="input" value={searchProvider} onChange={(event) => setSearchProvider(event.target.value)}>
                          <option value="github">GitHub</option>
                          <option value="nia">Nia</option>
                        </select>
                      </div>
                    </div>
                    <div className="field">
                      <span className="field-label">GitHub Token</span>
                      <input className="input" type="password" placeholder="ghp_..." value={githubToken} onChange={(event) => {
                        setGithubToken(event.target.value);
                        localStorage.setItem(GITHUB_TOKEN_KEY, event.target.value);
                      }} />
                    </div>
                  </div>
                  <div className="field">
                    <span className="field-label">Target repository</span>
                    <input className="input" value={targetRepo} onChange={(event) => {
                      setTargetRepo(event.target.value);
                      localStorage.setItem(TARGET_REPO_KEY, event.target.value);
                    }} />
                  </div>
                  <div className="row-between">
                    <div className="hgap-8">
                      <span className="iter-pill">{task.max_iterations} <span className="of">/ retries</span></span>
                      <span className="iter-pill">sandbox <span className="of">enabled</span></span>
                    </div>
                    <button className="btn primary" onClick={() => void handleCreateTask()} disabled={loading}>
                      Start task <ArrowIcon />
                    </button>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="eyebrow">Active task</div>
                    <h3>Task snapshot</h3>
                  </div>
                  <span className={`statuspill ${task.current_phase === "FAILED" ? "warn" : "ok"}`}>{task.id ? "Healthy" : "Idle"}</span>
                </div>
                <div className="card-body">
                  <div className="hero-phase-title">{task.id ? phaseSnapshotTitle(task.current_phase) : "No task"}</div>
                  <div className="helper" style={{ marginTop: 4, marginBottom: 14 }}>{phaseDescription(task.current_phase)}</div>
                  <div className="kv"><span className="k">Task ID</span><span className="v mono">{compactTaskId(task.id)}</span></div>
                  <div className="kv"><span className="k">Search provider</span><span className="v">{providerLabel(task.search_provider)}</span></div>
                  <div className="kv"><span className="k">Selected model</span><span className="v mono">{task.selected_model ?? "Pending"}</span></div>
                  <div className="kv"><span className="k">Constraints</span><span className="v">{task.bug_list_constraints.length} active</span></div>
                  <div className="kv"><span className="k">Updated</span><span className="v">{formatUpdated(task.updated_at)}</span></div>
                </div>
              </div>
            </div>

            <div className="row-between" style={{ marginBottom: 10 }}>
              <div>
                <div className="eyebrow" style={{ color: "var(--muted)" }}>Five-phase pipeline</div>
                <div style={{ fontSize: 13, color: "var(--muted)" }}>Tap a phase to inspect its inputs, outputs, and latency.</div>
              </div>
              <div className="hgap-8">
                <span className="iter-pill"><ClockIcon /> {totalDurationLabel(logs)} total</span>
                <span className="iter-pill">iter <strong style={{ marginLeft: 2 }}>{task.sandbox_iterations}</strong> <span className="of">/ {task.max_iterations}</span></span>
              </div>
            </div>

            <div className="phasestrip">
              {PHASES.map((phase, index) => {
                const status = phaseCardStatus(task.current_phase, phase.key);
                const active = index === activeIndex;
                return (
                  <button key={phase.key} className={`phase ${active ? "active" : status === "Pending" ? "pending" : ""}`} onClick={() => setView(phase.view)}>
                    <div className="row-between">
                      <div className="num">{phase.step}</div>
                      <span className="tag">{status}</span>
                    </div>
                    <h4>{phase.title}</h4>
                    <p>{phase.desc}</p>
                    <div className="bar"><i style={{ width: `${phaseProgress(task.current_phase, index)}%` }} /></div>
                    <div className="row-between" style={{ fontSize: 11, color: "var(--muted)" }}>
                      <span>Latency</span>
                      <span style={{ fontFamily: "var(--font-mono)" }}>{phaseLatency(logs, phase.step)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        <section className={`view ${view === "approval" ? "active" : ""}`}>
          <PageHeader
            crumbs={["Pipeline", "Approval console"]}
            title="Approval console"
            desc="Review the structured prompt, inspect the constraints the planner extracted, and decide whether Phase 4 should run."
            aside={
              <>
                <span className={`statuspill ${task.current_phase === "FAILED" ? "warn" : "ok"}`}>
                  {task.current_phase === "FAILED" ? "Rejected" : phaseIndex(task.current_phase) >= 3 ? <CheckIcon /> : null}
                  {approvalStateLabel(task.current_phase)}
                </span>
                <button className="btn" onClick={() => void handleReject()} disabled={!task.id || loading}>Reject</button>
                <button className="btn primary" onClick={() => void handleApprove()} disabled={!task.id || loading}>
                  Continue to Phase 4 <ArrowIcon />
                </button>
              </>
            }
          />
          <div className="workspace">
            <div className="approval-grid">
              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="eyebrow">Structured prompt</div>
                    <h3>Generated by planner · Phase 2</h3>
                  </div>
                  <span className="iter-pill" style={{ fontFamily: "var(--font-mono)" }}>{providerLabel(task.search_provider).toLowerCase()} · similar-repo</span>
                </div>
                <div className="card-body">
                  <div className="prompt-doc">
                    {renderPrompt(task.structured_prompt || task.original_prompt)}
                  </div>
                </div>
              </div>

              <div className="vstack-16">
                <div className="card">
                  <div className="card-head">
                    <div>
                      <div className="eyebrow">Review checklist</div>
                      <h3>Constraints · {task.bug_list_constraints.length} active</h3>
                    </div>
                    <span className="iter-pill">{task.bug_list_constraints.length ? "review ready" : "waiting"}</span>
                  </div>
                  <div className="card-body">
                    <div className="checklist">
                      {task.bug_list_constraints.length ? task.bug_list_constraints.map((constraint, index) => {
                        const passed = phaseIndex(task.current_phase) >= 3;
                        return (
                          <div key={`${constraint}-${index}`} className={`check-item ${passed ? "passed" : ""}`}>
                            <div className="check-box">{passed ? <CheckIcon /> : null}</div>
                            <div><div className="check-text">{constraint}</div></div>
                            <span className="check-tag" style={passed ? { background: "var(--ok-soft)", color: "var(--ok)" } : undefined}>{passed ? "pass" : "policy"}</span>
                          </div>
                        );
                      }) : <div className="helper">Constraints will appear after Phase 2 completes.</div>}
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="card-head">
                    <div>
                      <div className="eyebrow">Reviewer decision</div>
                      <h3>Comment</h3>
                    </div>
                  </div>
                  <div className="card-body vstack-12">
                    <textarea id="approval-editor" className="input" rows={3} defaultValue={task.structured_prompt ?? ""} />
                    <div className="row-between">
                      <span className="helper">Decision logs are immutable and attached to the task.</span>
                      <div className="hgap-8">
                        <button className="btn primary" onClick={() => void handleApprove()} disabled={!task.id || loading}>Approve</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className={`view ${view === "output" ? "active" : ""}`}>
          <PageHeader
            crumbs={["Pipeline", "Generated output"]}
            title="Generated output"
            desc="The model, code, and sandbox state produced by Phase 4 and Phase 5. Diff and review before opening the PR."
            aside={
              <>
                <span className="statuspill ok"><span className="dot" /> {outputHeaderLabel(task)}</span>
                <button className="btn" onClick={openDiff} disabled={!prUrl}><DiffIcon /> View diff</button>
                <button className="btn primary" onClick={openPr} disabled={!prUrl}><GithubIcon /> Open PR <ArrowIcon /></button>
              </>
            }
          />
          <div className="workspace">
            <div className="stats" style={{ marginBottom: 18 }}>
              <div className="stat">
                <div className="lbl">Selected model</div>
                <div className="val" style={{ fontSize: 18, fontFamily: "var(--font-mono)", letterSpacing: 0 }}>{task.selected_model ?? "Pending"}</div>
                <div className="desc">Picked during Phase 4 routing.</div>
              </div>
              <div className="stat">
                <div className="lbl">Current phase</div>
                <div className="val">{outputPhaseLabel(task.current_phase)}</div>
                <div className="meta"><span className="dot" /> {phaseDescription(task.current_phase)}</div>
              </div>
              <div className="stat">
                <div className="lbl">Sandbox iterations</div>
                <div className="val">{task.sandbox_iterations} <span className="unit">/ {task.max_iterations}</span></div>
                <div className="sparkbar">
                  {Array.from({ length: task.max_iterations }).map((_, index) => <i key={index} className={index < task.sandbox_iterations ? "on" : ""} style={{ height: index < task.sandbox_iterations ? "70%" : "30%" }} />)}
                </div>
              </div>
              <div className="stat">
                <div className="lbl">Search provider</div>
                <div className="val" style={{ fontSize: 18 }}>{providerLabel(task.search_provider)}</div>
                <div className="desc">Similar repository context attached during Phase 1.</div>
              </div>
            </div>

            <div className="output-grid">
              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="eyebrow">Delivery snapshot</div>
                    <h3>{task.generated_code ? "Code generated" : "Awaiting code"}</h3>
                  </div>
                </div>
                <div className="card-body">
                  <div className="kv"><span className="k">Task</span><span className="v mono">{compactTaskId(task.id)}</span></div>
                  <div className="kv"><span className="k">Constraints</span><span className="v">{task.bug_list_constraints.length}</span></div>
                  <div className="kv"><span className="k">PR branch</span><span className="v mono">{task.id ? `aegis/${task.id.slice(0, 8)}` : "Not opened"}</span></div>
                  <div className="kv"><span className="k">Updated</span><span className="v">{formatUpdated(task.updated_at)}</span></div>
                </div>
                <div className="card-rule" />
                <div className="card-body" style={{ paddingTop: 14 }}>
                  <div className="eyebrow" style={{ marginBottom: 8 }}>Phase log</div>
                  <div className="vstack-8">
                    {phaseLog.length ? phaseLog.map((entry, index) => (
                      <div key={`${entry.time}-${index}`} style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 10, alignItems: "start" }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)" }}>{entry.time}</span>
                        <span style={{ fontSize: 12.5, color: "var(--ink-2)" }}>{entry.message}</span>
                      </div>
                    )) : <div className="helper">No phase log recorded yet.</div>}
                  </div>
                </div>
              </div>

              <div className="card" style={{ padding: 0, background: "transparent", border: "none", boxShadow: "none" }}>
                <div className="codeblock">
                  <div className="ch">
                    <div className="dots"><i /><i /><i /></div>
                    <div className="lbl">workflow / handler.py · generated</div>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button className="btn" style={{ padding: "4px 8px", fontSize: 11, background: "rgba(255,255,255,0.06)", color: "var(--code-ink)", border: "1px solid var(--code-line)" }} onClick={copyCode}><CopyIcon /> Copy</button>
                    </div>
                  </div>
                  <pre className="code-plain">{task.generated_code || "# Awaiting generated code..."}</pre>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className={`view ${view === "logs" ? "active" : ""}`}>
          <PageHeader
            crumbs={["Pipeline", "Execution logs"]}
            title="Execution logs"
            desc="Real-time WebSocket events, sandbox messages, GitHub PR flow, and state transitions emitted by the backend."
            aside={
              <>
                <span className="live-chip"><span className="dot" /> Auto-refresh · {autoRefresh ? "on" : "off"}</span>
                <button className="btn" onClick={exportLog}>Export .log</button>
                <button className="btn primary" onClick={() => setTailFollow((value) => !value)}>{tailFollow ? "Tail follow" : "Tail paused"}</button>
              </>
            }
          />
          <div className="workspace">
            <div className="logs-grid">
              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="eyebrow">Task status</div>
                    <h3>{logsStatusTitle(task.current_phase)}</h3>
                  </div>
                  <span className={`statuspill ${task.current_phase === "FAILED" ? "warn" : "ok"}`}>{task.id ? "healthy" : "idle"}</span>
                </div>
                <div className="card-body">
                  <div className="kv"><span className="k">Task ID</span><span className="v mono">{compactTaskId(task.id)}</span></div>
                  <div className="kv"><span className="k">Search provider</span><span className="v">{providerLabel(task.search_provider)}</span></div>
                  <div className="kv"><span className="k">Iterations</span><span className="v">{task.sandbox_iterations} / {task.max_iterations}</span></div>
                  <div className="kv"><span className="k">Last update</span><span className="v">{formatUpdated(task.updated_at)}</span></div>
                </div>
              </div>

              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="eyebrow">Delivery flow</div>
                    <h3>{displayRepo(task.target_repo)}</h3>
                  </div>
                  <span className="iter-pill mono">{task.id ? `aegis/${task.id.slice(0, 8)}` : "branch pending"}</span>
                </div>
                <div className="card-body">
                  <div className="kv"><span className="k">Selected model</span><span className="v mono">{task.selected_model ?? "Pending"}</span></div>
                  <div className="kv"><span className="k">Constraint count</span><span className="v">{task.bug_list_constraints.length}</span></div>
                  <div className="kv"><span className="k">PR status</span><span className="v" style={{ color: prUrl ? "var(--ok)" : "var(--muted)" }}>{prUrl ? "open · awaiting review" : "Not opened"}</span></div>
                </div>
              </div>

              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="eyebrow">Event mix · last 5m</div>
                    <h3>{logs.length} events</h3>
                  </div>
                  <span className="iter-pill">live</span>
                </div>
                <div className="card-body">
                  {[
                    ["Info", eventMix.info, "var(--info)"],
                    ["OK", eventMix.ok, "var(--ok)"],
                    ["Review", eventMix.review, "var(--warn)"],
                    ["Error", eventMix.err, "var(--danger)"],
                  ].map(([label, value, color]) => (
                    <div key={String(label)} style={{ display: "grid", gridTemplateColumns: "70px 1fr 30px", gap: 10, alignItems: "center", padding: "6px 0" }}>
                      <span style={{ fontSize: 12, color: "var(--muted)" }}>{label}</span>
                      <span style={{ height: 6, background: "var(--bg-sub)", borderRadius: 999, overflow: "hidden" }}>
                        <span style={{ display: "block", height: "100%", width: `${eventMix.total ? (Number(value) / eventMix.total) * 100 : 0}%`, background: String(color) }} />
                      </span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, textAlign: "right" }}>{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="logterm">
              <div className="lh">
                <span style={{ display: "flex", gap: 6 }}><i /><i /><i /></span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>{task.id ? `~ aegis · stream://task/${task.id.slice(0, 8)}` : "~ aegis · stream://task/not-loaded"}</span>
                <span className="name">task-execution.log</span>
              </div>
              <div className="body" ref={terminalRef}>
                {logs.length ? logs.map((entry, index) => (
                  <div key={`${entry.time}-${index}`} className="row">
                    <span className="t">[{entry.time}]</span>
                    <span className={`lvl lvl-${entry.tone}`}>{entry.level}</span>
                    <span>{entry.message}</span>
                  </div>
                )) : <div className="row"><span className="t">[--:--:--]</span><span className="lvl lvl-info">INFO</span><span>No events yet.</span></div>}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function PageHeader({
  crumbs,
  title,
  desc,
  aside,
}: {
  crumbs: string[];
  title: string;
  desc: string;
  aside: React.ReactNode;
}) {
  return (
    <div className="pageheader">
      <div>
        <div className="crumbs">
          {crumbs.map((crumb, index) => (
            <span key={`${crumb}-${index}`}>
              {index > 0 ? <em>/</em> : null}
              <span>{crumb}</span>
            </span>
          ))}
        </div>
        <h1 className="page-title">{title}</h1>
        <p className="page-desc">{desc}</p>
      </div>
      <div className="header-aside">{aside}</div>
    </div>
  );
}

function renderPrompt(prompt: string | null) {
  if (!prompt) {
    return <div className="helper">No structured prompt available yet.</div>;
  }
  const sections = prompt.split(/\n(?=# )/g);
  return (
    <>
      <h2>Structured System Prompt</h2>
      {sections.map((section, sectionIndex) => {
        const [heading, ...lines] = section.split("\n");
        return (
          <div key={`${heading}-${sectionIndex}`}>
            <h3>{heading.replace(/^#\s*/, "")}</h3>
            {lines.filter(Boolean).map((line, lineIndex) => {
              const trimmed = line.trim();
              if (trimmed.startsWith("-")) {
                return <p key={`${sectionIndex}-${lineIndex}`}>• {trimmed.replace(/^-+\s*/, "")}</p>;
              }
              return <p key={`${sectionIndex}-${lineIndex}`}>{line}</p>;
            })}
          </div>
        );
      })}
    </>
  );
}

function phaseIndex(phase: string) {
  const order = [...PHASES.map((phaseMeta) => phaseMeta.key), "FINISHED", "FAILED"];
  const index = order.indexOf(phase);
  return index === -1 ? 0 : index;
}

function phaseHeadline(phase: string) {
  const labels: Record<string, string> = {
    "1_INTENT_PARSING": "Phase 1",
    "2_PRECHECK_GREPTILE": "Phase 2",
    "3_HUMAN_IN_THE_LOOP": "Phase 3",
    "4_COMPUTE_ROUTING": "Phase 4",
    "5_SANDBOX_TESTING": "Phase 5",
    FINISHED: "Finished",
    FAILED: "Failed",
  };
  return labels[phase] ?? "Unknown";
}

function phaseStatusLabel(phase: string) {
  if (phase === "FINISHED") return "done";
  if (phase === "FAILED") return "failed";
  return "running";
}

function phaseDescription(phase: string) {
  const descriptions: Record<string, string> = {
    "1_INTENT_PARSING": "Intent and context collection in progress.",
    "2_PRECHECK_GREPTILE": "Constraint extraction in progress.",
    "3_HUMAN_IN_THE_LOOP": "Waiting for reviewer approval.",
    "4_COMPUTE_ROUTING": "Code generation in flight.",
    "5_SANDBOX_TESTING": "Sandbox review and PR flow running.",
    FINISHED: "Backend marked task complete.",
    FAILED: "Workflow stopped before completion.",
  };
  return descriptions[phase] ?? "Status unavailable.";
}

function phaseSnapshotTitle(phase: string) {
  if (phase === "FINISHED") return "Finished";
  if (phase === "FAILED") return "Failed";
  return phaseHeadline(phase);
}

function providerLabel(provider: string | null) {
  return provider === "nia" ? "Nia" : "GitHub";
}

function displayRepo(targetRepo?: string | null) {
  if (!targetRepo) return TARGET_REPO;
  const repo = targetRepo.split("/").pop();
  return repo || TARGET_REPO;
}

function compactTaskId(taskId: string) {
  if (!taskId) return "Not loaded";
  return taskId.length > 18 ? `${taskId.slice(0, 8)}…${taskId.slice(-6)}` : taskId;
}

function formatUpdated(value: string) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · just now`;
}

function phaseCardStatus(currentPhase: string, phaseKey: string) {
  if (currentPhase === "FINISHED") return "Done";
  if (currentPhase === "FAILED") {
    if (phaseIndex(phaseKey) < phaseIndex(currentPhase)) return "Done";
    if (phaseIndex(phaseKey) === phaseIndex(currentPhase)) return "Failed";
    return "Pending";
  }
  if (phaseIndex(phaseKey) < phaseIndex(currentPhase)) return "Done";
  if (phaseIndex(phaseKey) === phaseIndex(currentPhase)) return "Running";
  return "Pending";
}

function phaseProgress(currentPhase: string, phaseIdx: number) {
  const currentIdx = phaseIndex(currentPhase);
  if (currentPhase === "FINISHED") return 100;
  if (phaseIdx < currentIdx) return 100;
  if (phaseIdx === currentIdx) {
    return currentPhase === "3_HUMAN_IN_THE_LOOP" ? 48 : 62;
  }
  return 0;
}

function phaseLatency(logs: LogEntry[], step: string) {
  const match = [...logs].reverse().find((entry) => entry.message.includes(`${step.replace(/^0/, "")}s`));
  const duration = match?.message.match(/(\d+)s/);
  return duration ? `${duration[1]}s` : "—";
}

function totalDurationLabel(logs: LogEntry[]) {
  const durations = logs
    .map((entry) => entry.message.match(/(\d+)s/g))
    .flat()
    .filter(Boolean) as string[];
  if (!durations.length) return "—";
  const total = durations.reduce((sum, current) => sum + Number(current.replace("s", "")), 0);
  return `${Math.floor(total / 60)}m ${total % 60}s`;
}

function outputHeaderLabel(task: BackendTask) {
  if (task.current_phase === "FINISHED") return "Sandbox passing";
  if (task.current_phase === "5_SANDBOX_TESTING") return "Sandbox running";
  if (task.current_phase === "4_COMPUTE_ROUTING") return "Code generating";
  if (task.current_phase === "FAILED") return "Task failed";
  return "Waiting";
}

function outputPhaseLabel(phase: string) {
  if (phase === "FINISHED") return <>Finished <span className="unit">· 5/5</span></>;
  if (phase === "FAILED") return "Failed";
  return phaseHeadline(phase);
}

function approvalStateLabel(phase: string) {
  if (phase === "FAILED") return "Rejected";
  if (phaseIndex(phase) >= phaseIndex("4_COMPUTE_ROUTING")) return "Approved";
  return "Pending review";
}

function logsStatusTitle(phase: string) {
  if (phase === "FINISHED") return "Finished · 5 of 5";
  if (phase === "FAILED") return "Failed";
  if (phase === "1_INTENT_PARSING") return "Phase 1 · 1 of 5";
  if (phase === "2_PRECHECK_GREPTILE") return "Phase 2 · 2 of 5";
  if (phase === "3_HUMAN_IN_THE_LOOP") return "Phase 3 · 3 of 5";
  if (phase === "4_COMPUTE_ROUTING") return "Phase 4 · 4 of 5";
  if (phase === "5_SANDBOX_TESTING") return "Phase 5 · 5 of 5";
  return "No active task";
}

function phasePillClass(phase: string) {
  if (phase === "FAILED") return "warn";
  if (phase === "4_COMPUTE_ROUTING" || phase === "5_SANDBOX_TESTING") return "info";
  if (phase === "FINISHED") return "ok";
  return "neutral";
}

function levelTone(level: string): LogLevel {
  if (level === "OK") return "ok";
  if (level === "REVIEW") return "review";
  if (level === "ERR" || level === "ERROR") return "err";
  return "info";
}

function inferLevel(message: string) {
  const lowered = message.toLowerCase();
  if (lowered.includes("error") || lowered.includes("fail") || lowered.includes("issue") || lowered.includes("timeout")) {
    return "ERR";
  }
  if (lowered.includes("review") || lowered.includes("approval")) {
    return "REVIEW";
  }
  if (lowered.includes("pass") || lowered.includes("approved") || lowered.includes("merged") || lowered.includes("opened")) {
    return "OK";
  }
  return "INFO";
}

export { App };
