import { authFetch } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const sandboxApi = {
  async status() {
    const res = await authFetch(`${API_URL}/api/sandbox/status`);
    return res.json();
  },

  async updateConfig(model: string) {
    const res = await authFetch(`${API_URL}/api/sandbox/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    return res.json();
  },

  async recreate() {
    const res = await authFetch(`${API_URL}/api/sandbox/recreate`, {
      method: "POST",
    });
    return res.json();
  },

  async stop() {
    const res = await authFetch(`${API_URL}/api/sandbox/stop`, {
      method: "POST",
    });
    return res.json();
  },

  async start() {
    const res = await authFetch(`${API_URL}/api/sandbox/start`, {
      method: "POST",
    });
    return res.json();
  },

  async getSandboxConnection() {
    const res = await authFetch(`${API_URL}/api/me/connections/github-sandbox`);
    return res.json();
  },

  async connectGitHub(token: string) {
    const res = await authFetch(`${API_URL}/api/me/connections/github-sandbox`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    return res.json();
  },

  async disconnectGitHub() {
    const res = await authFetch(`${API_URL}/api/me/connections/github-sandbox`, {
      method: "DELETE",
    });
    return res.json();
  },

  streamTask(taskId: string): EventSource {
    return new EventSource(`${API_URL}/api/sandbox/tasks/${taskId}/stream`);
  },
};
