import {
  AlertTriangle,
  Check,
  ChevronRight,
  Code2,
  FileCheck2,
  GitPullRequest,
  Network,
  Pause,
  Play,
  Route,
  ShieldCheck,
  Sparkles,
  TestTube2,
  X,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { approveTask, createTask, rejectTask } from './api';
import {
  addEvent,
  defaultRequest,
  demoCases,
  initialState,
  type WorkflowState,
  type WorkflowStatus,
} from './workflow';

const phaseMeta: Array<{
  status: WorkflowStatus;
  title: string;
  sponsor: string;
  icon: typeof Sparkles;
}> = [
  { status: 'context', title: 'Intent and Context', sponsor: 'Clod.io context seam', icon: Sparkles },
  { status: 'risk', title: 'Risk Guide', sponsor: 'AI preflight seam', icon: ShieldCheck },
  { status: 'pendingApproval', title: 'HITL Approval', sponsor: 'AegisHarness', icon: Pause },
  { status: 'execution', title: 'Compute and Generate', sponsor: 'Clod.io API seam', icon: Route },
  { status: 'sandbox', title: 'Sandbox and Repair', sponsor: 'AI TREX seam', icon: TestTube2 },
];

const runningStatuses: WorkflowStatus[] = ['context', 'risk', 'execution', 'sandbox', 'repair'];

const statusLabel = (status: WorkflowStatus) =>
  status
    .replace('pendingApproval', 'PENDING_APPROVAL')
    .replace('finished', 'FINISHED')
    .replace(/([a-z])([A-Z])/g, '$1_$2')
    .toUpperCase();

export function App() {
  const [state, setState] = useState<WorkflowState>(initialState);
  const [draftPrompt, setDraftPrompt] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState('');

  const canStart = !isRunning && ['idle', 'finished', 'failed', 'rejected'].includes(state.status);
  const awaitingApproval = state.status === 'pendingApproval';

  const activeIndex = useMemo(() => {
    if (state.status === 'idle') return -1;
    if (['context', 'clarification'].includes(state.status)) return 0;
    if (state.status === 'risk') return 1;
    if (state.status === 'pendingApproval') return 2;
    if (state.status === 'execution') return 3;
    return 4;
  }, [state.status]);

  const runPreApproval = async () => {
    setIsRunning(true);
    setError('');
    const request = state.userRequest.trim() || defaultRequest;
    setState(
      addEvent(
        { ...initialState, userRequest: request, status: 'context' },
        'task.received',
        'Task received',
        'Calling the local backend, which uses the Clod API key from .env.',
      ),
    );

    try {
      const created = await createTask(request);
      setDraftPrompt(created.prompt);
      setState(created);
    } catch (apiError) {
      const message = apiError instanceof Error ? apiError.message : 'Unknown backend error';
      setError(message);
      setState((current) =>
        addEvent(
          { ...current, status: 'failed' },
          'workflow.failed',
          'Backend request failed',
          message,
        ),
      );
    } finally {
      setIsRunning(false);
    }
  };

  const approveAndContinue = async () => {
    if (!state.taskId) {
      setError('No backend task id is available. Build the agent brief first.');
      return;
    }
    setIsRunning(true);
    setError('');
    setState(
      addEvent(
        { ...state, prompt: draftPrompt, status: 'execution' },
        'hitl.approved',
        'Human approval captured',
        'Backend is calling the configured live AI provider for generation and review.',
      ),
    );

    try {
      const approved = await approveTask(state.taskId, draftPrompt);
      setState(approved);
    } catch (apiError) {
      const message = apiError instanceof Error ? apiError.message : 'Unknown backend error';
      setError(message);
      setState((current) =>
        addEvent(
          { ...current, status: 'failed' },
          'workflow.failed',
          'Backend request failed',
          message,
        ),
      );
    } finally {
      setIsRunning(false);
    }
  };

  const reject = async () => {
    if (!state.taskId) return;
    setIsRunning(true);
    setError('');
    try {
      setState(await rejectTask(state.taskId));
    } catch (apiError) {
      const message = apiError instanceof Error ? apiError.message : 'Unknown backend error';
      setError(message);
    } finally {
      setIsRunning(false);
    }
  };

  const applyClarification = () => {
    setState((current) =>
      addEvent(
        { ...current, status: 'pendingApproval', confidence: 78 },
        'hitl.approval.requested',
        'Clarification applied',
        'Confidence threshold cleared after human edits.',
      ),
    );
  };

  const loadDemoCase = (request: string) => {
    setState({ ...initialState, userRequest: request });
    setDraftPrompt('');
  };

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <div className="eyebrow">Person C Mode: Prompt, Routing, Demo QA</div>
          <h1>AegisHarness</h1>
        </div>
        <div className="status-pill" data-status={state.status}>
          {runningStatuses.includes(state.status) ? <Play size={16} /> : <Network size={16} />}
          {statusLabel(state.status)}
        </div>
      </section>

      <section className="workspace">
        <div className="left-rail">
          <div className="panel intake">
            <div className="panel-title">
              <Code2 size={18} />
              Natural Language Intake
            </div>
            <textarea
              value={state.userRequest}
              onChange={(event) => setState({ ...state, userRequest: event.target.value })}
              disabled={isRunning || awaitingApproval}
              aria-label="Task request"
            />
            <button className="primary-action" onClick={runPreApproval} disabled={!canStart}>
              <Sparkles size={18} />
              Build Agent Brief
            </button>
          </div>

          <section className="panel demo-panel">
            <div className="panel-title">
              <FileCheck2 size={18} />
              Demo Cases
            </div>
            {demoCases.map((demo) => (
              <button
                className="demo-case"
                key={demo.title}
                onClick={() => loadDemoCase(demo.request)}
                disabled={isRunning || awaitingApproval}
              >
                <strong>{demo.title}</strong>
                <span>{demo.whyItWorks}</span>
              </button>
            ))}
          </section>

          <div className="phase-list">
            {phaseMeta.map((phase, index) => {
              const Icon = phase.icon;
              const phaseState = index < activeIndex ? 'done' : index === activeIndex ? 'active' : 'pending';
              return (
                <div className="phase-row" data-phase={phaseState} key={phase.title}>
                  <div className="phase-icon">
                    {phaseState === 'done' ? <Check size={16} /> : <Icon size={16} />}
                  </div>
                  <div>
                    <strong>{phase.title}</strong>
                    <span>{phase.sponsor}</span>
                  </div>
                  <ChevronRight size={16} />
                </div>
              );
            })}
          </div>
        </div>

        <div className="center-stage">
          <section className="panel brief-panel">
            <div className="panel-title">
              <FileCheck2 size={18} />
              HITL Markdown Brief
            </div>
            <textarea
              className="brief-editor"
              value={draftPrompt || state.prompt || 'Run intake to generate the agent-ready Markdown brief.'}
              onChange={(event) => setDraftPrompt(event.target.value)}
              disabled={!awaitingApproval && state.status !== 'clarification'}
              aria-label="Expanded Markdown brief"
            />
            <div className="brief-actions">
              <div className="confidence">
                <span>Confidence</span>
                <strong>{state.confidence}%</strong>
              </div>
              {state.status === 'clarification' && (
                <button className="secondary-action" onClick={applyClarification} disabled={isRunning}>
                  <AlertTriangle size={17} />
                  Apply Clarification
                </button>
              )}
              {awaitingApproval && (
                <>
                  <button className="secondary-action danger" onClick={reject} disabled={isRunning}>
                    <X size={17} />
                    Reject
                  </button>
                  <button className="primary-action" onClick={approveAndContinue} disabled={isRunning}>
                    <Check size={17} />
                    Approve and Execute
                  </button>
                </>
              )}
            </div>
          </section>

          <section className="panel audit-panel">
            <div className="panel-title">
              <GitPullRequest size={18} />
              Event Stream
            </div>
            {error && <div className="error-state">{error}</div>}
            <div className="event-list">
              {state.events.length === 0 ? (
                <div className="empty-state">No events yet. Submit a task to start the state machine.</div>
              ) : (
                state.events.map((event) => (
                  <article className="event-row" key={event.id}>
                    <time>{event.timestamp}</time>
                    <div>
                      <strong>{event.label}</strong>
                      <span>{event.type}</span>
                      <p>{event.detail}</p>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>

        <aside className="right-rail">
          <Metric title="References" value={state.references.length.toString()} label="Live AI context matches" />
          <Metric title="Risk Rules" value={state.risks.length.toString()} label="AI preflight constraints" />
          <Metric
            title="Greploop"
            value={`${state.repairAttempts}/${state.maxRepairAttempts}`}
            label="Hard stop enforced"
          />

          <section className="panel compact">
            <div className="panel-title">
              <Route size={18} />
              Difficulty and Route
            </div>
            {state.route ? (
              <div className="route-card">
                <strong>{state.route.model}</strong>
                <span>{state.route.provider}</span>
                <p>{state.route.rationale}</p>
                <div className="split-line">
                  <span>{state.route.budget}</span>
                  <span>Difficulty {state.route.difficulty}/5</span>
                </div>
              </div>
            ) : (
              <div className="empty-state">Awaiting HITL approval.</div>
            )}
          </section>

          <section className="panel compact">
            <div className="panel-title">
              <TestTube2 size={18} />
              Sandbox Result
            </div>
            <div className="review-status" data-review={state.review.status}>
              {state.review.status}
            </div>
            <p className="muted">{state.review.summary}</p>
            {state.review.tests.map((test) => (
              <div className="test-line" key={test}>
                {test}
              </div>
            ))}
          </section>

          <section className="panel compact">
            <div className="panel-title">
              <Code2 size={18} />
              Final Code Output
            </div>
            {state.code ? (
              <div className="code-card">
                <strong>{state.code.title}</strong>
                <span>{state.code.summary}</span>
                <pre>
                  <code>{state.code.patch}</code>
                </pre>
              </div>
            ) : (
              <div className="empty-state">Generated code appears after approved execution.</div>
            )}
          </section>
        </aside>
      </section>
    </main>
  );
}

function Metric({ title, value, label }: { title: string; value: string; label: string }) {
  return (
    <section className="metric">
      <span>{title}</span>
      <strong>{value}</strong>
      <p>{label}</p>
    </section>
  );
}
