const API_BASE = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

// --- Notes ---
export interface Note {
  id: string;
  title: string;
  content: string;
  images: string[];
  createdAt: string;
  updatedAt: string;
}

export interface NoteCreate {
  title: string;
  content: string;
}

export interface NoteUpdate {
  title?: string;
  content?: string;
}

// --- Ideas ---
export interface Idea {
  id: string;
  title: string;
  description: string;
  images: string[];
  status: "draft" | "refined";
  refinedDraft: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface IdeaCreate {
  title: string;
  description?: string;
}

export interface IdeaUpdate {
  title?: string;
  description?: string;
}

// --- Research ---
export interface Citation {
  url: string;
  title: string;
}

export interface Research {
  id: string;
  title: string;
  query: string;
  mode: "web_search" | "deep_research";
  status: "pending" | "completed" | "failed";
  result: string | null;
  citations: Citation[];
  ideaId: string | null;
  error: string | null;
  createdAt: string;
  updatedAt: string;
}

// --- Specs ---
export interface Spec {
  id: string;
  title: string;
  content: string;
  type: "foundation" | "feature";
  parentId: string | null;
  ideaId: string | null;
  status: "draft" | "optimized";
  createdAt: string;
  updatedAt: string;
}

export interface SpecCreate {
  title: string;
  content?: string;
  type?: "foundation" | "feature";
  parentId?: string;
  ideaId?: string;
}

export interface SpecUpdate {
  title?: string;
  content?: string;
  type?: string;
  parentId?: string;
  status?: string;
}

// --- Agents ---
export interface AgentInfo {
  id: string;
  name: string;
  type: "gateway" | "orchestrator" | "specialist";
  model?: string;
  status: string;
  tools?: string[];
}

export interface AgentEdge {
  from: string;
  to: string;
}

export interface AgentStatus {
  agents: AgentInfo[];
  edges: AgentEdge[];
}

// --- API helpers ---
async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const notesApi = {
  list: () => fetchApi<Note[]>("/api/notes"),
  get: (id: string) => fetchApi<Note>(`/api/notes/${id}`),
  create: (data: NoteCreate) =>
    fetchApi<Note>("/api/notes", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: NoteUpdate) =>
    fetchApi<Note>(`/api/notes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetchApi<void>(`/api/notes/${id}`, { method: "DELETE" }),
};

export const ideasApi = {
  list: () => fetchApi<Idea[]>("/api/ideas"),
  get: (id: string) => fetchApi<Idea>(`/api/ideas/${id}`),
  create: (data: IdeaCreate) =>
    fetchApi<Idea>("/api/ideas", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: IdeaUpdate) =>
    fetchApi<Idea>(`/api/ideas/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetchApi<void>(`/api/ideas/${id}`, { method: "DELETE" }),
  refine: (id: string) =>
    fetchApi<Idea>(`/api/ideas/${id}/refine`, { method: "POST" }),
};

export const researchApi = {
  list: () => fetchApi<Research[]>("/api/research"),
  get: (id: string) => fetchApi<Research>(`/api/research/${id}`),
  delete: (id: string) => fetchApi<void>(`/api/research/${id}`, { method: "DELETE" }),
  webSearch: (query: string, ideaId?: string) =>
    fetchApi<Research>("/api/research/search", {
      method: "POST",
      body: JSON.stringify({ query, mode: "web_search", idea_id: ideaId }),
    }),
  deepResearch: (query: string, ideaId?: string) =>
    fetchApi<Research>("/api/research/deep", {
      method: "POST",
      body: JSON.stringify({ query, mode: "deep_research", idea_id: ideaId }),
    }),
  listByIdea: (ideaId: string) => fetchApi<Research[]>(`/api/ideas/${ideaId}/research`),
};

export const specsApi = {
  list: () => fetchApi<Spec[]>("/api/specs"),
  get: (id: string) => fetchApi<Spec>(`/api/specs/${id}`),
  create: (data: SpecCreate) =>
    fetchApi<Spec>("/api/specs", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: SpecUpdate) =>
    fetchApi<Spec>(`/api/specs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetchApi<void>(`/api/specs/${id}`, { method: "DELETE" }),
  optimize: (id: string) =>
    fetchApi<Spec>(`/api/specs/${id}/optimize`, { method: "POST" }),
  generate: (ideaId: string) =>
    fetchApi<{ success: boolean; specs: Array<{ id: string; title: string; type: string }> }>(
      "/api/specs/generate",
      { method: "POST", body: JSON.stringify({ idea_id: ideaId }) },
    ),
};

export const agentsApi = {
  status: () => fetchApi<AgentStatus>("/api/agents/status"),
};

// Dev Task types
export interface DevStage {
  name: string;
  status: string;
  output?: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface DevArtifact {
  name: string;
  type: string;
  data?: string;
}

export interface DevIteration {
  iterationIndex: number;
  label: string;
  specPartId?: string;
  stages: DevStage[];
  workspacePath?: string;
}

export interface DevTask {
  id: string;
  title: string;
  specId?: string;
  status: string;
  mode?: string;
  skillIds?: string[];
  stages: DevStage[];
  iterations: DevIteration[];
  currentIteration?: number;
  artifacts: DevArtifact[];
  createdAt: string;
  updatedAt: string;
}

export const devApi = {
  list: () => fetchApi<DevTask[]>("/api/dev"),
  get: (id: string) => fetchApi<DevTask>(`/api/dev/${id}`),
  create: (data: { title: string; specId?: string; mode?: string; skillIds?: string[] }) =>
    fetchApi<DevTask>("/api/dev", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetchApi<void>(`/api/dev/${id}`, { method: "DELETE" }),
  trigger: (id: string, mode?: string) =>
    fetchApi<DevTask>(`/api/dev/${id}/trigger`, { method: "POST", body: JSON.stringify(mode ? { mode } : {}) }),
};

/* ── Skills ── */

export interface InstalledSkill {
  name: string;
  description: string;
  source: string;
  version?: string;
  fileCount?: number;
}

export const skillsApi = {
  listInstalled: () =>
    fetchApi<{ skills: InstalledSkill[] }>("/api/agents/skills"),
  search: (q: string) =>
    fetchApi<{ results: { name: string; description: string; url: string; repo: string }[] }>(`/api/agents/skills/search?q=${encodeURIComponent(q)}`),
  install: (repo: string, skillName: string) =>
    fetchApi<{ name: string; status: string; error?: string }>("/api/agents/skills/install", { method: "POST", body: JSON.stringify({ repo, skillName }) }),
  installLocal: (sourcePath: string, name: string) =>
    fetchApi<{ name: string; status: string; error?: string }>("/api/agents/skills/install-local", { method: "POST", body: JSON.stringify({ sourcePath, name }) }),
  delete: (name: string) =>
    fetchApi<{ name: string; success: boolean }>(`/api/agents/skills/${encodeURIComponent(name)}`, { method: "DELETE" }),
  suggestForSpec: (specId: string) =>
    fetchApi<{ skillIds: string[] }>(`/api/dev/suggest-skills?specId=${encodeURIComponent(specId)}`),
};

export function getVoiceWebSocketUrl(): string {
  const wsBase = API_BASE.replace("http://", "ws://").replace("https://", "wss://");
  return `${wsBase}/ws/voice`;
}
