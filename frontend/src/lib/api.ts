import { getMsalInstance, loginScopes } from "./msal-config";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getAccessToken(): Promise<string | null> {
  const clientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID;
  if (!clientId) return null;

  try {
    const instance = getMsalInstance();
    const accounts = instance.getAllAccounts();
    if (accounts.length === 0) return null;

    const response = await instance.acquireTokenSilent({
      ...loginScopes,
      account: accounts[0],
    });
    return response.accessToken;
  } catch {
    return null;
  }
}

export async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = await getAccessToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(url, { ...init, headers });
}

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
  images?: string[];
}

export interface NoteUpdate {
  title?: string;
  content?: string;
  images?: string[];
}

export interface Idea {
  id: string;
  title: string;
  description: string;
  images: string[];
  attachments: string[];
  status: "draft" | "refined";
  refinedDraft: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface IdeaCreate {
  title: string;
  description?: string;
  images?: string[];
  attachments?: string[];
}

export interface IdeaUpdate {
  title?: string;
  description?: string;
  images?: string[];
  attachments?: string[];
}

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

export interface ResearchCreate {
  query: string;
  mode?: "web_search" | "deep_research";
  idea_id?: string;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await authFetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail ?? `${res.status} ${res.statusText}`;
    throw new Error(detail);
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
  refineStream: async (id: string, onChunk: (text: string) => void): Promise<string> => {
    const resp = await authFetch(`${API_BASE}/api/ideas/${id}/refine/stream`, { method: "POST" });
    if (!resp.ok) throw new Error(`Refine stream failed: ${resp.status}`);
    const reader = resp.body?.getReader();
    if (!reader) throw new Error("No response body");
    const decoder = new TextDecoder();
    let full = "";
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") break;
          full += data;
          onChunk(full);
        }
      }
    }
    return full;
  },
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
  linkToIdea: (researchId: string, ideaId: string) =>
    fetchApi<Research>(`/api/research/${researchId}/link`, {
      method: "PATCH",
      body: JSON.stringify({ ideaId }),
    }),
  unlinkFromIdea: (researchId: string) =>
    fetchApi<Research>(`/api/research/${researchId}/link`, {
      method: "PATCH",
      body: JSON.stringify({ ideaId: null }),
    }),
};

export interface AgentInfo {
  id: string;
  name: string;
  type: "gateway" | "orchestrator" | "specialist";
  model?: string;
  status: string;
  tools?: string[];
  mcpServers?: string[];
}

export interface AgentEdge {
  from: string;
  to: string;
}

export interface AgentStatus {
  agents: AgentInfo[];
  edges: AgentEdge[];
}

export const agentsApi = {
  status: () => fetchApi<AgentStatus>("/api/agents/status"),
};

// Specs
export interface Spec {
  id: string;
  title: string;
  content: string;
  type: "foundation" | "feature";
  parentId: string | null;
  ideaId: string | null;
  status: "draft" | "optimized" | "in-development" | "developed";
  devTaskId?: string | null;
  formatVersion?: string;
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
      { method: "POST", body: JSON.stringify({ idea_id: ideaId }) }
    ),
  addFeature: (specId: string, description: string) =>
    fetchApi<{
      success: boolean;
      feature_name: string;
      spec_id: string;
      dev_task_extended: boolean;
      pipeline_triggered: boolean;
    }>(`/api/specs/${specId}/add-feature`, {
      method: "POST",
      body: JSON.stringify({ description }),
    }),
  importOpenspec: async (files: File[]): Promise<{ foundationId: string; featureCount: number; changesFound: number }> => {
    const form = new FormData();
    for (const file of files) {
      const f = file as File & { webkitRelativePath?: string };
      const relPath = f.webkitRelativePath || f.name;
      // Strip the top-level folder from the path
      const stripped = relPath.split("/").slice(1).join("/");
      form.append("files", file, stripped || file.name);
    }
    // Extract folder name from first file's relative path
    const firstRel = (files[0] as File & { webkitRelativePath?: string }).webkitRelativePath || "";
    const folderName = firstRel.split("/")[0] || "imported-project";
    form.append("folder_name", folderName);
    const res = await authFetch(`${API_BASE}/api/specs/import-openspec`, { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Import failed" }));
      throw new Error(err.detail || "Import failed");
    }
    return res.json();
  },
};

export async function uploadImage(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await authFetch(`${API_BASE}/api/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  const data = await res.json();
  return data.url;
}

export function getVoiceWebSocketUrl(): string {
  const wsBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
    .replace("http://", "ws://")
    .replace("https://", "wss://");
  return `${wsBase}/ws/voice`;
}

export function getUploadUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export async function getVoiceAccessToken(): Promise<string | null> {
  return getAccessToken();
}

// ── Development Tasks ──────────────────────────────────────────

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
  iterationIndex?: number | null;
}

export interface DevIteration {
  iterationIndex: number;
  label: string;
  specPartId?: string;
  stages: DevStage[];
  workspacePath?: string;
}

export interface SquadMember {
  name: string;
  role: string;
  expertise: string;
  status: string; // idle | working | done
}

export interface SquadInfo {
  teamMembers: SquadMember[];
}

export interface DevTask {
  id: string;
  title: string;
  specId?: string;
  mode: string; // mock | sequence
  status: string;
  skillIds?: string[];
  squad?: SquadInfo;
  currentIteration: number;
  iterations: DevIteration[];
  stages: DevStage[]; // legacy flat view (iteration 0)
  artifacts: DevArtifact[];
  decisions?: { question: string; answer: string; stage: string; timestamp: string }[];
  premiumRequests?: number;
  createdAt: string;
  updatedAt: string;
}

export interface DevTaskCreate {
  title: string;
  specId?: string;
  mode?: string;
  skillIds?: string[];
}

export const devApi = {
  list: (): Promise<DevTask[]> => fetchApi("/api/dev"),
  get: (id: string): Promise<DevTask> => fetchApi(`/api/dev/${id}`),
  create: (data: DevTaskCreate): Promise<DevTask> =>
    fetchApi("/api/dev", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> =>
    fetchApi(`/api/dev/${id}`, { method: "DELETE" }),
  trigger: (id: string, mode?: string): Promise<DevTask> =>
    fetchApi(`/api/dev/${id}/trigger`, { method: "POST", body: JSON.stringify(mode ? { mode } : {}), headers: { "Content-Type": "application/json" } }),
  downloadUrl: (id: string): string => `${API_BASE}/api/dev/${id}/download`,
};

/* ── Skills ── */

export interface InstalledSkill {
  name: string;
  description: string;
  source: string;
  npxCommand?: string;
  activatedAt?: string;
}

export const skillsApi = {
  listInstalled: (): Promise<{ skills: InstalledSkill[] }> => fetchApi("/api/agents/skills"),
  search: (q: string): Promise<{ results: { name: string; description: string; url: string; repo: string; skillDir?: string }[] }> =>
    fetchApi(`/api/agents/skills/search?q=${encodeURIComponent(q)}`),
  activate: (repo: string, skillName: string, npxCommand: string, description: string): Promise<{ name: string; success: boolean; error?: string }> =>
    fetchApi("/api/agents/skills/install", { method: "POST", body: JSON.stringify({ repo, skillName, npxCommand, description }) }),
  deactivate: (name: string): Promise<{ name: string; success: boolean }> =>
    fetchApi(`/api/agents/skills/${encodeURIComponent(name)}`, { method: "DELETE" }),
  suggestForSpec: (specId: string): Promise<{ skillIds: string[] }> =>
    fetchApi(`/api/dev/suggest-skills?specId=${encodeURIComponent(specId)}`),
  uploadLocal: async (skillName: string, files: File[]): Promise<{ success: boolean; skillName: string; uploadedFiles: string[]; message: string }> => {
    const form = new FormData();
    files.forEach((f) => {
      // Preserve subfolder structure: strip the top-level folder from webkitRelativePath
      const relPath = (f as File & { webkitRelativePath?: string }).webkitRelativePath;
      const subPath = relPath ? relPath.split("/").slice(1).join("/") : f.name;
      form.append("files", f, subPath);
    });
    const resp = await authFetch(`${API_BASE}/api/dev/skills/upload-local?skill_name=${encodeURIComponent(skillName)}`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return resp.json();
  },
};

/* ── Spec Dev Task link ── */

export const specDevApi = {
  getDevTask: (specId: string): Promise<{ devTask: { id: string; title: string; mode: string; status: string } | null }> =>
    fetchApi(`/api/specs/${specId}/dev-task`),
};

/* ── Marketing Videos ── */

export interface MarketingVideo {
  id: string;
  title: string;
  devTaskId: string | null;
  specId: string | null;
  status: "pending" | "scripting" | "generating" | "composing" | "completed" | "failed";
  videoPath: string | null;
  videoUrl: string | null;
  scriptContent: string | null;
  durationSeconds: number | null;
  error: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface MarketingVideoCreate {
  title: string;
  devTaskId: string;
}

export const marketingApi = {
  list: (): Promise<MarketingVideo[]> => fetchApi("/api/marketing"),
  get: (id: string): Promise<MarketingVideo> => fetchApi(`/api/marketing/${id}`),
  create: (data: MarketingVideoCreate): Promise<MarketingVideo> =>
    fetchApi("/api/marketing", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string): Promise<{ success: boolean }> =>
    fetchApi(`/api/marketing/${id}`, { method: "DELETE" }),
  trigger: (id: string): Promise<{ success: boolean; message: string }> =>
    fetchApi(`/api/marketing/${id}/trigger`, { method: "POST" }),
  listByDevTask: (devTaskId: string): Promise<MarketingVideo[]> =>
    fetchApi(`/api/marketing/by-dev-task/${devTaskId}`),
  videoUrl: (id: string): string => `${API_BASE}/api/marketing/${id}/video`,
  fetchVideoBlob: async (id: string): Promise<string> => {
    const res = await authFetch(`${API_BASE}/api/marketing/${id}/video`);
    if (!res.ok) throw new Error("Failed to fetch video");
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
};

/* ── User Profile ── */

export interface UserProfile {
  id: string;
  userId: string;
  displayName: string;
  email: string;
  locale: string;
  avatarUrl: string | null;
  profilePhotoUrl: string | null;
  lastLoginAt?: string;
}

export const profileApi = {
  get: () => fetchApi<UserProfile>("/api/me"),
  updateLocale: (locale: string) =>
    fetchApi<UserProfile>("/api/me", { method: "PATCH", body: JSON.stringify({ locale }) }),
  updateProfile: (data: Record<string, unknown>) =>
    fetchApi<UserProfile>("/api/me", { method: "PATCH", body: JSON.stringify(data) }),
  getPremiumUsage: () =>
    fetchApi<{ total: number; usage: Record<string, number> }>("/api/me/premium-usage"),
};

export const userApi = {
  getProfile: (): Promise<UserProfile> => fetchApi<UserProfile>("/api/me"),
  uploadPhoto: async (file: File): Promise<{ success: boolean; photoUrl: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await authFetch(`${API_BASE}/api/me/photo`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },
  getPhotoUrl: (): string => `${API_BASE}/api/me/photo`,
  /** Fetch profile photo via authenticated API and return an object URL for <img src>. */
  getPhotoObjectUrl: async (): Promise<string | null> => {
    try {
      const res = await authFetch(`${API_BASE}/api/me/photo`);
      if (!res.ok) return null;
      const blob = await res.blob();
      return URL.createObjectURL(blob);
    } catch {
      return null;
    }
  },
};

/* ── To-Do Tasks (Microsoft To-Do) ── */

export interface Todo {
  id: string;
  title: string;
  isCompleted: boolean;
  notes?: string;
  dueDate?: string;
}

export interface TodoCreate {
  title: string;
  notes?: string;
  dueDate?: string;
}

export interface TodoUpdate {
  title?: string;
  notes?: string;
  dueDate?: string;
  isCompleted?: boolean;
}

export const todosApi = {
  list: () => fetchApi<Todo[]>("/api/todos"),
  get: (id: string) => fetchApi<Todo>(`/api/todos/${id}`),
  create: (data: TodoCreate) =>
    fetchApi<Todo>("/api/todos", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: TodoUpdate) =>
    fetchApi<Todo>(`/api/todos/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetchApi<void>(`/api/todos/${id}`, { method: "DELETE" }),
};

/* ── Connected Accounts ── */

export interface ConnectionStatus {
  connected: boolean;
  connectedAt?: string;
}

export const connectionsApi = {
  microsoftTodo: {
    status: () => fetchApi<ConnectionStatus>("/api/me/connections/microsoft-todo"),
    connect: () =>
      fetchApi<{ authUrl?: string; connected?: boolean; connectedAt?: string }>(
        "/api/me/connections/microsoft-todo",
        { method: "POST" },
      ),
    disconnect: () =>
      fetchApi<ConnectionStatus>("/api/me/connections/microsoft-todo", { method: "DELETE" }),
  },
};
