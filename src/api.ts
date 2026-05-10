import type { WorkflowState, WorkflowStatus } from './workflow';

const API_BASE_URL = 'http://127.0.0.1:8000';

type BackendTask = {
  id: number;
  request: string;
  status: string;
  confidence: number;
  prompt: string;
  references: WorkflowState['references'];
  risks: WorkflowState['risks'];
  route?: WorkflowState['route'];
  code?: WorkflowState['code'];
  repair_attempts: number;
  max_iterations: number;
  review: WorkflowState['review'];
  events: WorkflowState['events'];
};

const statusMap: Record<string, WorkflowStatus> = {
  IDLE: 'idle',
  CONTEXT: 'context',
  RISK: 'risk',
  PENDING_APPROVAL: 'pendingApproval',
  EXECUTION: 'execution',
  SANDBOX: 'sandbox',
  REPAIR: 'repair',
  FINISHED: 'finished',
  FAILED: 'failed',
  REJECTED: 'rejected',
};

const normalizeTask = (task: BackendTask): WorkflowState => ({
  taskId: task.id,
  status: statusMap[task.status] ?? 'failed',
  userRequest: task.request,
  prompt: task.prompt,
  confidence: task.confidence,
  references: task.references ?? [],
  risks: task.risks ?? [],
  route: task.route,
  code: task.code,
  repairAttempts: task.repair_attempts ?? 0,
  maxRepairAttempts: task.max_iterations ?? 3,
  review: task.review ?? {
    status: 'pending',
    summary: 'No sandbox review has run yet.',
    tests: [],
  },
  events: (task.events ?? []).map((event) => ({
    ...event,
    label: event.label ?? event.type,
  })),
});

const postJson = async <T>(path: string, body: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with HTTP ${response.status}`);
  }
  return payload;
};

export const createTask = async (request: string) => {
  const task = await postJson<BackendTask>('/api/tasks', { request });
  return normalizeTask(task);
};

export const approveTask = async (taskId: number, prompt: string) => {
  const task = await postJson<BackendTask>(`/api/tasks/${taskId}/approve`, { prompt });
  return normalizeTask(task);
};

export const rejectTask = async (taskId: number) => {
  const task = await postJson<BackendTask>(`/api/tasks/${taskId}/reject`, {});
  return normalizeTask(task);
};
