export type BackendTask = {
  id: string;
  original_prompt: string;
  structured_prompt: string | null;
  bug_list_constraints: string[];
  current_phase: string;
  search_provider: string;
  difficulty_score: number | null;
  selected_model: string | null;
  generated_code: string | null;
  sandbox_iterations: number;
  max_iterations: number;
  created_at: string;
  updated_at: string;
};

export type HealthResponse = {
  status: string;
  greptile_api_key_loaded?: boolean;
  clod_api_key_loaded?: boolean;
  gemini_api_key_loaded?: boolean;
};

async function parseJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : JSON.stringify(payload?.detail ?? payload);
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return payload as T;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/health");
  return parseJson<HealthResponse>(response);
}

export async function createTask(request: string, searchProvider: string): Promise<BackendTask> {
  const response = await fetch("/api/v1/tasks/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      request,
      search_provider: searchProvider,
    }),
  });
  return parseJson<BackendTask>(response);
}

export async function loadTask(taskId: string): Promise<BackendTask> {
  const response = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
  return parseJson<BackendTask>(response);
}

export async function approveTask(taskId: string, editedPrompt: string): Promise<BackendTask> {
  const response = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      approved: true,
      edited_prompt: editedPrompt || null,
    }),
  });
  return parseJson<BackendTask>(response);
}

export async function rejectTask(taskId: string): Promise<BackendTask> {
  const response = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/reject`, {
    method: "POST",
  });
  return parseJson<BackendTask>(response);
}
