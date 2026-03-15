"use client";

import { useEffect, useState, useCallback } from "react";
import { IconSettings, IconBrandGithub, IconCheck, IconX, IconPlugConnected } from "@tabler/icons-react";
import { sandboxApi } from "@/lib/sandbox-api";

export default function SettingsPage() {
  const [githubConnected, setGithubConnected] = useState(false);
  const [githubConnectedAt, setGithubConnectedAt] = useState("");
  const [todoConnected, setTodoConnected] = useState(false);
  const [todoConnectedAt, setTodoConnectedAt] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchConnections = useCallback(async () => {
    try {
      const [sandbox, todo] = await Promise.all([
        sandboxApi.getSandboxConnection(),
        fetch(`${API_URL}/api/me/connections/microsoft-todo`, { credentials: "include" }).then((r) => r.json()),
      ]);
      setGithubConnected(sandbox.connected || false);
      setGithubConnectedAt(sandbox.connectedAt || "");
      setTodoConnected(todo.connected || false);
      setTodoConnectedAt(todo.connectedAt || "");
    } catch {
      // ignore
    }
  }, [API_URL]);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const handleConnectGitHub = async () => {
    if (!tokenInput.trim()) return;
    setConnecting(true);
    try {
      const result = await sandboxApi.connectGitHub(tokenInput.trim());
      if (result.connected) {
        setGithubConnected(true);
        setGithubConnectedAt(result.connectedAt || "");
        setTokenInput("");
        setNotification({ type: "success", message: "GitHub sandbox connected!" });
      }
    } catch {
      setNotification({ type: "error", message: "Failed to connect" });
    } finally {
      setConnecting(false);
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const handleDisconnectGitHub = async () => {
    try {
      await sandboxApi.disconnectGitHub();
      setGithubConnected(false);
      setGithubConnectedAt("");
      setNotification({ type: "success", message: "GitHub sandbox disconnected" });
    } catch {
      setNotification({ type: "error", message: "Failed to disconnect" });
    }
    setTimeout(() => setNotification(null), 3000);
  };

  return (
    <div className="min-h-screen bg-[#0F0F1A] p-6">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 flex items-center gap-3">
          <IconSettings className="w-6 h-6 text-cyan-400" />
          <h1 className="text-2xl font-bold text-white">Settings</h1>
        </div>

        {/* Notification */}
        {notification && (
          <div
            className={`mb-4 rounded-lg px-4 py-3 text-sm ${
              notification.type === "success" ? "bg-green-900/40 text-green-300 border border-green-500/30" : "bg-red-900/40 text-red-300 border border-red-500/30"
            }`}
          >
            {notification.message}
          </div>
        )}

        {/* Connections Section */}
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <IconPlugConnected className="w-5 h-5 text-gray-400" />
            Connections
          </h2>

          {/* GitHub Copilot Sandbox */}
          <div className="rounded-xl border border-white/10 bg-white/5 p-5">
            <div className="flex items-center gap-3 mb-3">
              <IconBrandGithub className="w-5 h-5 text-white" />
              <div>
                <h3 className="font-medium text-white">GitHub Copilot Sandbox</h3>
                <p className="text-xs text-gray-400">Connect your GitHub account for the Copilot CLI sandbox</p>
              </div>
            </div>

            {githubConnected ? (
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-green-400">
                  <IconCheck className="w-4 h-4" />
                  Connected {githubConnectedAt && `· ${new Date(githubConnectedAt).toLocaleDateString()}`}
                </span>
                <button
                  onClick={handleDisconnectGitHub}
                  className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Paste your GitHub personal access token..."
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-gray-500 focus:border-cyan-400 focus:outline-none"
                />
                <button
                  onClick={handleConnectGitHub}
                  disabled={connecting || !tokenInput.trim()}
                  className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors"
                >
                  {connecting ? "Connecting..." : "Connect"}
                </button>
              </div>
            )}
          </div>

          {/* Microsoft To-Do */}
          <div className="rounded-xl border border-white/10 bg-white/5 p-5">
            <div className="flex items-center gap-3 mb-3">
              <IconCheck className="w-5 h-5 text-blue-400" />
              <div>
                <h3 className="font-medium text-white">Microsoft To-Do</h3>
                <p className="text-xs text-gray-400">Connect Microsoft To-Do for task management</p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              {todoConnected ? (
                <span className="flex items-center gap-2 text-sm text-green-400">
                  <IconCheck className="w-4 h-4" />
                  Connected {todoConnectedAt && `· ${new Date(todoConnectedAt).toLocaleDateString()}`}
                </span>
              ) : (
                <span className="flex items-center gap-2 text-sm text-gray-500">
                  <IconX className="w-4 h-4" />
                  Not Connected
                </span>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
