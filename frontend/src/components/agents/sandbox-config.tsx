"use client";

import { useEffect, useState, useCallback } from "react";
import { IconServer, IconRefresh, IconBrandGithub, IconCheck, IconX } from "@tabler/icons-react";
import { sandboxApi } from "@/lib/sandbox-api";

const AVAILABLE_MODELS = [
  { value: "claude-sonnet-4", label: "Claude Sonnet 4" },
  { value: "claude-sonnet-4.5", label: "Claude Sonnet 4.5" },
  { value: "gpt-4.1", label: "GPT-4.1" },
  { value: "gpt-5.1", label: "GPT-5.1" },
  { value: "gpt-5.2", label: "GPT-5.2" },
];

interface SandboxConfigProps {
  className?: string;
}

export function SandboxConfig({ className }: SandboxConfigProps) {
  const [status, setStatus] = useState<string>("loading");
  const [model, setModel] = useState<string>("claude-sonnet-4");
  const [githubConnected, setGithubConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await sandboxApi.status();
      setStatus(data.status || "not_configured");
      setModel(data.config?.model || "claude-sonnet-4");
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
      // revert on error
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
    stopped: "text-gray-400",
    error: "text-red-400",
    not_configured: "text-gray-500",
    loading: "text-gray-500",
  }[status] || "text-gray-500";

  return (
    <div className={`rounded-xl border border-white/10 bg-white/5 p-6 ${className || ""}`}>
      <div className="flex items-center gap-3 mb-4">
        <IconServer className="w-5 h-5 text-cyan-400" />
        <h3 className="text-lg font-semibold text-white">Sandbox Config</h3>
      </div>

      <div className="space-y-4">
        {/* Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Status</span>
          <span className={`text-sm font-medium capitalize ${statusColor}`}>
            {status === "not_configured" ? "Not Configured" : status}
          </span>
        </div>

        {/* Model Selection */}
        <div>
          <label className="text-sm text-gray-400 block mb-1">Default CLI Model</label>
          <select
            value={model}
            onChange={(e) => handleModelChange(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-cyan-400 focus:outline-none"
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m.value} value={m.value} className="bg-gray-900">
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {/* GitHub Auth */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">GitHub Auth</span>
          <div className="flex items-center gap-2">
            {githubConnected ? (
              <span className="flex items-center gap-1 text-sm text-green-400">
                <IconCheck className="w-4 h-4" /> Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-sm text-gray-500">
                <IconX className="w-4 h-4" /> Not Connected
              </span>
            )}
            <a href="/settings" className="text-xs text-cyan-400 hover:underline">
              Manage
            </a>
          </div>
        </div>

        {/* Recreate Button */}
        <button
          onClick={handleRecreate}
          disabled={loading || status === "provisioning"}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-white hover:bg-white/10 disabled:opacity-50 transition-colors"
        >
          <IconRefresh className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Recreating..." : "Recreate Sandbox"}
        </button>
      </div>
    </div>
  );
}
