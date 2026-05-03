declare global {
  interface Window {
    hermesVibe?: {
      platform: string;
      getBackendUrl?: () => Promise<string>;
      getBackendStatus?: () => Promise<BackendStatus>;
      restartBackend?: (options?: { hermesHome?: string; bootstrapHermesHome?: boolean }) => Promise<BackendStatus>;
    };
  }
}

let resolvedApiBase: string | null = null;

async function getApiBase(): Promise<string> {
  if (resolvedApiBase) return resolvedApiBase;
  if (import.meta.env.VITE_API_BASE) {
    const envApiBase = import.meta.env.VITE_API_BASE;
    resolvedApiBase = envApiBase;
    return envApiBase;
  }
  if (window.hermesVibe?.getBackendUrl) {
    const electronApiBase = await window.hermesVibe.getBackendUrl();
    resolvedApiBase = electronApiBase;
    return electronApiBase;
  }
  const defaultApiBase = 'http://127.0.0.1:8000';
  resolvedApiBase = defaultApiBase;
  return defaultApiBase;
}

export type HealthResponse = {
  status: string;
  hermes_home: { path: string };
};

export type ModelProvider = {
  id: string;
  display_name: string;
  auth_status: string;
  models: { id: string; display_name: string; context_window?: number | null }[];
};

export type DashboardProjection = {
  overview: {
    status: string;
    progress_percent: number;
    completed_count: number;
    in_progress_count: number;
    touched_file_count: number;
    blocker_count: number;
    concept_count: number;
    decision_count: number;
    next_action: string;
    last_activity: string;
  };
  implementation: {
    current_goal: string;
    completed_changes: string[];
    in_progress_changes: string[];
    touched_files: string[];
    important_decisions: string[];
    blockers: string[];
    test_status: string;
    next_steps: string[];
  };
  activity: { kind: string; summary: string; stream: string; tool: string }[];
  concepts: { concept: string; short_summary: string }[];
  decisions: { user_request: string; outcome: string }[];
  before_after: { file_path: string; before_summary: string; after_summary: string }[];
  errors: { error_message: string; root_cause_summary: string }[];
};

export type RuntimeActivityItem = DashboardProjection['activity'][number];

export type BackendStatus = {
  state: 'stopped' | 'starting' | 'running' | 'error';
  url: string;
  logs: string[];
  hermesHome?: string;
  exitCode?: number | null;
};

export type DashboardEvent = {
  id: string;
  session_id: string;
  type: string;
  payload: Record<string, unknown>;
  source: string;
  created_at: string;
};

export type RuntimeMessage = {
  role: 'user' | 'assistant' | 'system';
  content: string;
  provider?: string;
  model?: string;
  agent_id?: string;
  agent_name?: string;
  system_prompt?: string;
};

export type AgentProfile = {
  id: string;
  name: string;
  role: string;
  system_prompt: string;
  provider?: string | null;
  model?: string | null;
  skills: string[];
  created_at: string;
  updated_at: string;
  archived_at?: string | null;
};

export type AgentProfileInput = {
  name: string;
  role: string;
  system_prompt: string;
  provider?: string | null;
  model?: string | null;
  skills: string[];
};

export type CodingSession = {
  id: string;
  title: string;
  goal: string;
  created_at: string;
  updated_at: string;
  archived_at?: string | null;
};

export type CodingSessionInput = {
  title: string;
  goal: string;
};

export type SessionDeduplicateResult = {
  archived_count: number;
  groups: {
    key: { title: string; goal: string };
    keep_session_id: string;
    archived_session_ids: string[];
  }[];
};

export type MemoryFile = {
  path: string;
  size: number;
};

export type MemoryFileContent = {
  path: string;
  content: string;
};

export type SkillFile = MemoryFile;

export type SkillFileContent = MemoryFileContent;

export type HermesHomeStatus = {
  path: string;
  paths: Record<string, { path: string; exists: boolean; kind: string }>;
};

export type HermesConfig = {
  path: string;
  content: string;
};

export type HonchoStatus = {
  path: string;
  exists: boolean;
  file_count: number;
  total_size: number;
  recent_files: { path: string; size: number; modified_at: number }[];
  app_database_path: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${await getApiBase()}/health`);
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return response.json();
}

export async function getHermesHomeStatus(): Promise<HermesHomeStatus> {
  const response = await fetch(`${await getApiBase()}/hermes/home`);
  if (!response.ok) throw new Error(`Hermes home failed: ${response.status}`);
  return response.json();
}

export async function setHermesHome(path: string, bootstrap = false): Promise<HermesHomeStatus> {
  const response = await fetch(`${await getApiBase()}/hermes/home`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, bootstrap }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Hermes home update failed: ${response.status} ${detail}`);
  }
  return response.json();
}

export async function readHermesConfig(): Promise<HermesConfig> {
  const response = await fetch(`${await getApiBase()}/hermes/config`);
  if (!response.ok) throw new Error(`Hermes config read failed: ${response.status}`);
  return response.json();
}

export async function saveHermesConfig(content: string): Promise<void> {
  const response = await fetch(`${await getApiBase()}/hermes/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, reason: 'Hermes Vibe config editor save' }),
  });
  if (!response.ok) throw new Error(`Hermes config save failed: ${response.status}`);
}

export async function getHonchoStatus(): Promise<HonchoStatus> {
  const response = await fetch(`${await getApiBase()}/honcho/status`);
  if (!response.ok) throw new Error(`Honcho status failed: ${response.status}`);
  return response.json();
}

export async function getBackendStatus(): Promise<BackendStatus | null> {
  return window.hermesVibe?.getBackendStatus ? window.hermesVibe.getBackendStatus() : null;
}

export async function restartBackend(options?: { hermesHome?: string; bootstrapHermesHome?: boolean }): Promise<BackendStatus | null> {
  if (!window.hermesVibe?.restartBackend) return null;
  resolvedApiBase = null;
  const status = await window.hermesVibe.restartBackend(options);
  resolvedApiBase = status.url;
  return status;
}

export async function getModelProviders(): Promise<ModelProvider[]> {
  const response = await fetch(`${await getApiBase()}/models/providers`);
  if (!response.ok) throw new Error(`Model providers failed: ${response.status}`);
  return response.json();
}

export async function listAgents(includeArchived = false): Promise<AgentProfile[]> {
  const query = includeArchived ? '?include_archived=true' : '';
  const response = await fetch(`${await getApiBase()}/agents${query}`);
  if (!response.ok) throw new Error(`Agent list failed: ${response.status}`);
  return response.json();
}

export async function createAgent(input: AgentProfileInput): Promise<AgentProfile> {
  const response = await fetch(`${await getApiBase()}/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`Agent create failed: ${response.status}`);
  return response.json();
}

export async function updateAgent(agentId: string, input: Partial<AgentProfileInput>): Promise<AgentProfile> {
  const response = await fetch(`${await getApiBase()}/agents/${agentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`Agent update failed: ${response.status}`);
  return response.json();
}

export async function archiveAgent(agentId: string): Promise<AgentProfile> {
  const response = await fetch(`${await getApiBase()}/agents/${agentId}/archive`, { method: 'POST' });
  if (!response.ok) throw new Error(`Agent archive failed: ${response.status}`);
  return response.json();
}

export async function restoreAgent(agentId: string): Promise<AgentProfile> {
  const response = await fetch(`${await getApiBase()}/agents/${agentId}/restore`, { method: 'POST' });
  if (!response.ok) throw new Error(`Agent restore failed: ${response.status}`);
  return response.json();
}

export async function deleteAgent(agentId: string): Promise<void> {
  const response = await fetch(`${await getApiBase()}/agents/${agentId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Agent delete failed: ${response.status}`);
}

export async function listSessions(includeArchived = false): Promise<CodingSession[]> {
  const query = includeArchived ? '?include_archived=true' : '';
  const response = await fetch(`${await getApiBase()}/sessions${query}`);
  if (!response.ok) throw new Error(`Session list failed: ${response.status}`);
  return response.json();
}

export async function createSession(input: CodingSessionInput): Promise<CodingSession> {
  const response = await fetch(`${await getApiBase()}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`Session create failed: ${response.status}`);
  return response.json();
}

export async function updateSession(sessionId: string, input: Partial<CodingSessionInput>): Promise<CodingSession> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`Session update failed: ${response.status}`);
  return response.json();
}

export async function archiveSession(sessionId: string): Promise<CodingSession> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}/archive`, { method: 'POST' });
  if (!response.ok) throw new Error(`Session archive failed: ${response.status}`);
  return response.json();
}

export async function restoreSession(sessionId: string): Promise<CodingSession> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}/restore`, { method: 'POST' });
  if (!response.ok) throw new Error(`Session restore failed: ${response.status}`);
  return response.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Session delete failed: ${response.status}`);
}

export async function deduplicateSessions(): Promise<SessionDeduplicateResult> {
  const response = await fetch(`${await getApiBase()}/sessions/deduplicate`, { method: 'POST' });
  if (!response.ok) throw new Error(`Session deduplicate failed: ${response.status}`);
  return response.json();
}

export async function listSessionEvents(sessionId: string): Promise<DashboardEvent[]> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}/events`);
  if (!response.ok) throw new Error(`Session events failed: ${response.status}`);
  return response.json();
}

export async function listMemoryFiles(): Promise<MemoryFile[]> {
  const response = await fetch(`${await getApiBase()}/memory/files`);
  if (!response.ok) throw new Error(`Memory list failed: ${response.status}`);
  return response.json();
}

export async function readMemoryFile(path: string): Promise<MemoryFileContent> {
  const response = await fetch(`${await getApiBase()}/memory/files/${encodePath(path)}`);
  if (!response.ok) throw new Error(`Memory read failed: ${response.status}`);
  return response.json();
}

export async function saveMemoryFile(path: string, content: string): Promise<void> {
  const response = await fetch(`${await getApiBase()}/memory/files/${encodePath(path)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, reason: 'Hermes Vibe memory editor save' }),
  });
  if (!response.ok) throw new Error(`Memory save failed: ${response.status}`);
}

export async function listSkillFiles(): Promise<SkillFile[]> {
  const response = await fetch(`${await getApiBase()}/skills/files`);
  if (!response.ok) throw new Error(`Skill list failed: ${response.status}`);
  return response.json();
}

export async function readSkillFile(path: string): Promise<SkillFileContent> {
  const response = await fetch(`${await getApiBase()}/skills/files/${encodePath(path)}`);
  if (!response.ok) throw new Error(`Skill read failed: ${response.status}`);
  return response.json();
}

export async function saveSkillFile(path: string, content: string): Promise<void> {
  const response = await fetch(`${await getApiBase()}/skills/files/${encodePath(path)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, reason: 'Hermes Vibe skill editor save' }),
  });
  if (!response.ok) throw new Error(`Skill save failed: ${response.status}`);
}

export async function getDashboard(sessionId: string): Promise<DashboardProjection> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}/dashboard`);
  if (!response.ok) throw new Error(`Dashboard failed: ${response.status}`);
  return response.json();
}

export async function sendMessage(sessionId: string, message: RuntimeMessage): Promise<DashboardEvent[]> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
  });
  if (!response.ok) throw new Error(`Message send failed: ${response.status}`);
  const body = await response.json() as { events: DashboardEvent[] };
  return body.events;
}

export async function streamMessage(
  sessionId: string,
  message: RuntimeMessage,
  onEvent: (event: DashboardEvent) => void | Promise<void>,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${await getApiBase()}/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
    signal,
  });
  if (!response.ok) throw new Error(`Message stream failed: ${response.status}`);
  if (!response.body) throw new Error('Message stream unavailable');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';
    for (const frame of frames) {
      const event = parseSseFrame(frame);
      if (event) await onEvent(event);
    }
  }

  buffer += decoder.decode();
  const trailingEvent = parseSseFrame(buffer);
  if (trailingEvent) await onEvent(trailingEvent);
}

function parseSseFrame(frame: string): DashboardEvent | null {
  const dataLine = frame.split('\n').find((line) => line.startsWith('data: '));
  if (!dataLine) return null;
  return JSON.parse(dataLine.slice('data: '.length)) as DashboardEvent;
}

function encodePath(path: string): string {
  return path.split('/').map((part) => encodeURIComponent(part)).join('/');
}
