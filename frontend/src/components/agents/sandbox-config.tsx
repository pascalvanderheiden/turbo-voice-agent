"use client";

import { useEffect, useState, useCallback } from "react";
import { IconServer, IconRefresh, IconCheck, IconX } from "@tabler/icons-react";
import { sandboxApi } from "@/lib/sandbox-api";

const AVAILABLE_MODELS = [
  { value: "claude-opus-4.6", label: "Claude Opus 4.6" },
  { value: "gpt-5.3-codex", label: "GPT-5.3-Codex" },
  { value: "claude-sonnet-4.6", label: "Claude Sonnet 4.6" },
];

interface SandboxConfigProps {
  className?: string;
}

export function SandboxConfig({ className }: SandboxConfigProps) {
  const [status, setStatus] = useState<string>("loading");
  const [model, setModel] = useState<string>("claude-opus-4.6");
  const [githubConnected, setGithubConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await sandboxApi.status();
      setStatus(data.status || "not_configured");
      setModel(data.config?.model || "claude-opus-4.6");
      setGithubConnected(data.githubConnected || false);
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleModelChange = async (newModel: string) => {
    setModel(newModel);
    try {
      await sandboxApi.updateConfig(newModel);
    } catch {
      fetchStatus();
    }
  };

  const handleRecreate = async () => {
    setLoading(true);
    try {
      await sandboxApi.recreate();
      setStatus("provisioning");
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const statusColor = {
    ready: "text-green-400",
    provisioning: "text-yellow-400",
    stopped: "text-[var(--color-text-muted)]",
    error: "text-red-400",
    not_configured: "text-[var(--color-text-muted)]",
    loading: "text-[var(--color-text-muted)]",
  }[status] || "text-[var(--color-text-muted)]";

  return (
    <div
      className={`bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 ${className || ""}`}
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)]/15">
          <IconServer size={16} stroke={1.5} className="text-[var(--color-brand-cyan)]" />
        </div>
        <h2 className="text-sm font-medium text-[var(--color-text-muted)]">Sandbox Config</h2>
      </div>

      <div className="space-y-4">
        {/* Status */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-[var(--color-text-muted)]">Status</span>
          <span className={`text-xs font-medium capitalize ${statusColor}`}>
            {status === "not_configured" ? "Not Configured" : status}
          </span>
        </div>

        {/* Model Selection */}
        <div>
          <label className="text-xs text-[var(--color-text-muted)] block mb-1.5">
            Default CLI Model
          </label>
          <select
            value={model}
            onChange={(e) => handleModelChange(e.target.value)}
            className="w-full rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors"
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {/* GitHub Auth */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-[var(--color-text-muted)]">GitHub Auth</span>
          <div className="flex items-center gap-2">
            {githubConnected ? (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <IconCheck size={14} stroke={1.5} /> Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
                <IconX size={14} stroke={1.5} /> Not Connected
              </span>
            )}
            <a
              href="/settings"
              className="text-xs text-[var(--color-brand-cyan)] hover:underline"
            >
              Manage
            </a>
          </div>
        </div>

        {/* Recreate Button */}
        <button
          onClick={handleRecreate}
          disabled={loading || status === "provisioning"}
          className="flex w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] px-4 py-2 text-sm text-[var(--color-text-primary)] disabled:opacity-50 transition-colors"
        >
          <IconRefresh size={14} className={loading ? "animate-spin" : ""} />
          {loading ? "Recreating..." : "Recreate Sandbox"}
        </button>
      </div>
    </div>
  );
}
