"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { IconServer, IconRefresh, IconCheck, IconX, IconLoader2 } from "@tabler/icons-react";
import { sandboxApi } from "@/lib/sandbox-api";

const AVAILABLE_MODELS = [
  { value: "claude-opus-4.6", label: "Claude Opus 4.6" },
  { value: "gpt-5.3-codex", label: "GPT-5.3-Codex" },
  { value: "claude-sonnet-4.6", label: "Claude Sonnet 4.6" },
];

const STATUS_CONFIG: Record<string, { label: string; dot: string; text: string; pulse?: boolean }> = {
  ready:          { label: "Running",        dot: "bg-green-400",  text: "text-green-400" },
  busy:           { label: "Busy",           dot: "bg-yellow-400", text: "text-yellow-400", pulse: true },
  provisioning:   { label: "Provisioning",   dot: "bg-yellow-400", text: "text-yellow-400", pulse: true },
  stopped:        { label: "Stopped",        dot: "bg-[var(--color-text-muted)]", text: "text-[var(--color-text-muted)]" },
  error:          { label: "Error",          dot: "bg-red-400",    text: "text-red-400" },
  not_configured: { label: "Not Configured", dot: "bg-[var(--color-text-muted)]", text: "text-[var(--color-text-muted)]" },
  loading:        { label: "Loading",        dot: "bg-[var(--color-text-muted)]", text: "text-[var(--color-text-muted)]" },
};

interface SandboxConfigProps {
  className?: string;
}

export function SandboxConfig({ className }: SandboxConfigProps) {
  const [status, setStatus] = useState<string>("loading");
  const [activeTasks, setActiveTasks] = useState<number>(0);
  const [model, setModel] = useState<string>("claude-opus-4.6");
  const [githubConnected, setGithubConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await sandboxApi.status();
      const rawStatus = data.status || "not_configured";
      const tasks = data.activeTasks ?? 0;
      setActiveTasks(tasks);
      setStatus(rawStatus === "ready" && tasks > 0 ? "busy" : rawStatus);
      setModel(data.config?.model || "claude-opus-4.6");
      setGithubConnected(data.githubConnected || false);
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    pollRef.current = setInterval(fetchStatus, 15_000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
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

  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.not_configured;

  return (
    <div
      className={`bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 ${className || ""}`}
    >
      {/* Header with live status badge */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)]/15">
            <IconServer size={16} stroke={1.5} className="text-[var(--color-brand-cyan)]" />
          </div>
          <h2 className="text-sm font-medium text-[var(--color-text-muted)]">Sandbox</h2>
        </div>
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
          <span className="relative flex h-2 w-2">
            {cfg.pulse && (
              <span className={`absolute inset-0 rounded-full ${cfg.dot} opacity-75 animate-ping`} />
            )}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${cfg.dot}`} />
          </span>
          <span className={`text-[11px] font-medium ${cfg.text}`}>{cfg.label}</span>
          {status === "busy" && (
            <span className="text-[10px] text-[var(--color-text-muted)]">
              ({activeTasks} task{activeTasks !== 1 ? "s" : ""})
            </span>
          )}
        </div>
      </div>

      <div className="space-y-4">
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

        {/* Create / Recreate Button */}
        <button
          onClick={handleRecreate}
          disabled={loading || status === "provisioning" || status === "busy"}
          className="flex w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] px-4 py-2 text-sm text-[var(--color-text-primary)] disabled:opacity-50 transition-colors"
        >
          {loading ? (
            <IconLoader2 size={14} className="animate-spin" />
          ) : (
            <IconRefresh size={14} />
          )}
          {loading
            ? "Creating..."
            : status === "stopped" || status === "not_configured"
              ? "Create Sandbox"
              : "Recreate Sandbox"}
        </button>
      </div>
    </div>
  );
}
