"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  IconSettings,
  IconBrandGithub,
  IconCheck,
  IconX,
  IconPlugConnected,
  IconPlugConnectedX,
  IconCamera,
  IconLanguage,
  IconSun,
  IconMoon,
  IconUser,
  IconSparkles,
} from "@tabler/icons-react";
import { useTheme } from "next-themes";
import { useI18n, type Locale } from "@/lib/i18n";
import { userApi, profileApi, connectionsApi } from "@/lib/api";
import { sandboxApi } from "@/lib/sandbox-api";
import { toast } from "sonner";

export default function SettingsPage() {
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Profile
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Connections
  const [githubConnected, setGithubConnected] = useState(false);
  const [githubConnectedAt, setGithubConnectedAt] = useState("");
  const [todoConnected, setTodoConnected] = useState(false);
  const [todoConnectedAt, setTodoConnectedAt] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectingTodo, setConnectingTodo] = useState(false);

  // Premium usage
  const [premiumTotal, setPremiumTotal] = useState(0);
  const [premiumUsage, setPremiumUsage] = useState<Record<string, number>>({});

  useEffect(() => setMounted(true), []);

  // Handle OAuth callback query params (after redirect from Microsoft consent)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const todoResult = params.get("todo_connected");
    if (todoResult === "success") {
      toast.success("Microsoft To-Do connected!");
      setTodoConnected(true);
      setTodoConnectedAt(new Date().toISOString());
      window.history.replaceState({}, "", "/settings");
    } else if (todoResult === "error") {
      toast.error("Microsoft To-Do connection failed");
      window.history.replaceState({}, "", "/settings");
    }
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const profile = await profileApi.get();
      setDisplayName(profile.displayName || "");
      setEmail(profile.email || "");
    } catch {
      // ignore
    }
  }, []);

  const fetchPhoto = useCallback(async () => {
    try {
      const url = await userApi.getPhotoObjectUrl();
      if (url) setPhotoUrl(url);
    } catch {
      // ignore — no photo available
    }
  }, []);

  const fetchConnections = useCallback(async () => {
    try {
      const [sandbox, todo] = await Promise.all([
        sandboxApi.getSandboxConnection().catch(() => ({ connected: false, connectedAt: "" })),
        connectionsApi.microsoftTodo.status().catch(() => ({ connected: false, connectedAt: "" })),
      ]);
      setGithubConnected(sandbox.connected || false);
      setGithubConnectedAt((sandbox as { connectedAt?: string }).connectedAt || "");
      setTodoConnected(todo.connected || false);
      setTodoConnectedAt((todo as { connectedAt?: string }).connectedAt || "");
    } catch {
      // ignore
    }
  }, []);

  const fetchPremiumUsage = useCallback(async () => {
    try {
      const data = await profileApi.getPremiumUsage();
      setPremiumTotal(data.total || 0);
      setPremiumUsage(data.usage || {});
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchProfile();
    fetchPhoto();
    fetchConnections();
    fetchPremiumUsage();
  }, [fetchProfile, fetchPhoto, fetchConnections, fetchPremiumUsage]);

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      // Show local preview immediately
      const localPreview = URL.createObjectURL(file);
      setPhotoUrl(localPreview);
      await userApi.uploadPhoto(file);
      toast.success("Photo updated");
    } catch {
      // Revert preview on failure
      setPhotoUrl(null);
      toast.error("Photo upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleToggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    profileApi.updateProfile({ theme: next }).catch(() => {});
  };

  const handleConnectGitHub = async () => {
    if (!tokenInput.trim()) return;
    setConnecting(true);
    try {
      const result = await sandboxApi.connectGitHub(tokenInput.trim());
      if (result.connected) {
        setGithubConnected(true);
        setGithubConnectedAt(result.connectedAt || "");
        setTokenInput("");
        toast.success("GitHub sandbox connected!");
      }
    } catch {
      toast.error("Failed to connect");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnectGitHub = async () => {
    try {
      await sandboxApi.disconnectGitHub();
      setGithubConnected(false);
      setGithubConnectedAt("");
      toast.success("GitHub sandbox disconnected");
    } catch {
      toast.error("Failed to disconnect");
    }
  };

  const handleConnectTodo = async () => {
    setConnectingTodo(true);
    try {
      const result = await connectionsApi.microsoftTodo.connect();
      if (result.connected) {
        // AUTH_DISABLED mode: auto-connected, no redirect needed
        setTodoConnected(true);
        setTodoConnectedAt(result.connectedAt || "");
        toast.success("Microsoft To-Do connected");
        setConnectingTodo(false);
      } else if (result.authUrl) {
        // Production: redirect to OAuth consent
        window.location.href = result.authUrl;
      }
    } catch {
      toast.error("Failed to start Microsoft To-Do connection");
      setConnectingTodo(false);
    }
  };

  const handleDisconnectTodo = async () => {
    try {
      await connectionsApi.microsoftTodo.disconnect();
      setTodoConnected(false);
      setTodoConnectedAt("");
      toast.success("Microsoft To-Do disconnected");
    } catch {
      toast.error("Failed to disconnect");
    }
  };

  function getInitials(name: string): string {
    return name
      .split(" ")
      .map((p) => p[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold gradient-brand-text">
          {t("nav.settings") || "Settings"}
        </h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">
          Manage your profile, preferences, and connected accounts
        </p>
      </div>

      {/* Profile Section */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] bg-[var(--color-brand-pink)]/15">
            <IconUser size={16} stroke={1.5} className="text-[var(--color-brand-pink)]" />
          </div>
          <h2 className="text-sm font-medium text-[var(--color-text-muted)]">Profile</h2>
        </div>

        <div className="flex items-center gap-4 mb-5">
          {/* Avatar */}
          <div className="relative group">
            {photoUrl ? (
              <img
                src={photoUrl}
                alt={displayName}
                className="w-16 h-16 rounded-full object-cover"
              />
            ) : (
              <div className="w-16 h-16 rounded-full bg-[var(--color-brand-pink)]/20 text-[var(--color-brand-pink)] flex items-center justify-center text-lg font-bold">
                {getInitials(displayName || email || "U")}
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={handlePhotoUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
            >
              <IconCamera size={18} className="text-white" />
            </button>
          </div>
          <div>
            <p className="font-medium text-[var(--color-text-primary)]">{displayName || "—"}</p>
            <p className="text-sm text-[var(--color-text-muted)]">{email || "—"}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Theme */}
          <div className="flex items-center justify-between p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              {mounted && (theme === "dark" ? <IconMoon size={16} stroke={1.5} /> : <IconSun size={16} stroke={1.5} />)}
              <span>{t("theme.toggle") || "Theme"}</span>
            </div>
            <button
              onClick={handleToggleTheme}
              className="px-3 py-1 rounded-[var(--radius-md)] text-xs font-medium bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-brand-pink)]/15 text-[var(--color-text-primary)] transition-colors"
            >
              {mounted && (theme === "dark" ? "Light" : "Dark")}
            </button>
          </div>

          {/* Language */}
          <div className="flex items-center justify-between p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <IconLanguage size={16} stroke={1.5} />
              <span>{t("header.language") || "Language"}</span>
            </div>
            <div className="flex items-center gap-1 bg-[var(--color-bg-tertiary)] rounded-full p-0.5">
              {(["en", "nl"] as Locale[]).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setLocale(lang)}
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold transition-colors ${
                    locale === lang
                      ? "bg-[var(--color-brand-pink)] text-white"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  {lang.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Connections Section */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)]/15">
            <IconPlugConnected size={16} stroke={1.5} className="text-[var(--color-brand-cyan)]" />
          </div>
          <h2 className="text-sm font-medium text-[var(--color-text-muted)]">
            {t("connections.title") || "Connected Accounts"}
          </h2>
        </div>

        <div className="space-y-4">
          {/* GitHub Copilot Sandbox */}
          <div className="p-4 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <div className="flex items-center gap-3 mb-3">
              <IconBrandGithub size={20} stroke={1.5} className="text-[var(--color-text-primary)]" />
              <div>
                <h3 className="text-sm font-medium text-[var(--color-text-primary)]">
                  GitHub Copilot Sandbox
                </h3>
                <p className="text-xs text-[var(--color-text-muted)]">
                  Connect your GitHub account for the Copilot CLI sandbox
                </p>
              </div>
            </div>

            {githubConnected ? (
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-xs text-green-400">
                  <IconCheck size={14} stroke={1.5} />
                  Connected{" "}
                  {githubConnectedAt &&
                    `· ${new Date(githubConnectedAt).toLocaleDateString()}`}
                </span>
                <button
                  onClick={handleDisconnectGitHub}
                  className="rounded-[var(--radius-md)] border border-red-500/30 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Paste your GitHub personal access token..."
                  className="flex-1 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors"
                />
                <button
                  onClick={handleConnectGitHub}
                  disabled={connecting || !tokenInput.trim()}
                  className="rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors"
                >
                  {connecting ? "Connecting..." : "Connect"}
                </button>
              </div>
            )}
          </div>

          {/* Microsoft To-Do */}
          <div className="p-4 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <div className="flex items-center gap-3 mb-3">
              <IconSettings size={20} stroke={1.5} className="text-blue-400" />
              <div>
                <h3 className="text-sm font-medium text-[var(--color-text-primary)]">
                  Microsoft To-Do
                </h3>
                <p className="text-xs text-[var(--color-text-muted)]">
                  Connect Microsoft To-Do for task management
                </p>
              </div>
            </div>

            {todoConnected ? (
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-xs text-green-400">
                  <IconCheck size={14} stroke={1.5} />
                  Connected{" "}
                  {todoConnectedAt &&
                    `· ${new Date(todoConnectedAt).toLocaleDateString()}`}
                </span>
                <button
                  onClick={handleDisconnectTodo}
                  className="rounded-[var(--radius-md)] border border-red-500/30 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <button
                onClick={handleConnectTodo}
                disabled={connectingTodo}
                className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-brand-pink)] transition-colors disabled:opacity-50"
              >
                <IconPlugConnectedX size={16} stroke={1.5} />
                <span>
                  {connectingTodo
                    ? (t("connections.connecting") || "Connecting…")
                    : (t("connections.connectTodo") || "Connect Microsoft To-Do")}
                </span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Premium Usage Section */}
      <PremiumUsageChart total={premiumTotal} usage={premiumUsage} />
    </div>
  );
}


function PremiumUsageChart({
  total,
  usage,
}: {
  total: number;
  usage: Record<string, number>;
}) {
  // Build last 6 months of data
  const allMonths: { key: string; label: string; count: number }[] = [];
  const now = new Date();
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const label = d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
    const count = usage[key] || 0;
    if (count > 0) allMonths.push({ key, label, count });
  }
  // Fallback: show current month if no data
  if (allMonths.length === 0) {
    const key = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const label = now.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
    allMonths.push({ key, label, count: 0 });
  }
  const months = allMonths;

  const maxCount = Math.max(...months.map((m) => m.count), 2000);

  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="flex items-center justify-center w-8 h-8 rounded-[var(--radius-md)] bg-[var(--color-brand-purple)]/15">
          <IconSparkles size={16} stroke={1.5} className="text-[var(--color-brand-purple)]" />
        </div>
        <div className="flex-1">
          <h2 className="text-sm font-medium text-[var(--color-text-muted)]">
            Premium Requests
          </h2>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold gradient-brand-text">
            {total.toLocaleString()}
          </span>
          <span className="text-xs text-[var(--color-text-muted)] ml-1">total</span>
        </div>
      </div>

      {/* Bar chart */}
      <div className="flex items-end gap-2 h-40">
        {months.map((m) => {
          const heightPct = maxCount > 0 ? (m.count / maxCount) * 100 : 0;
          return (
            <div key={m.key} className="flex-1 flex flex-col items-center gap-1.5">
              <span className="text-[10px] font-medium text-[var(--color-text-secondary)] tabular-nums">
                {m.count > 0 ? m.count.toLocaleString() : ""}
              </span>
              <div className="w-full flex-1 flex items-end">
                <div
                  className="w-full rounded-t-[var(--radius-sm)] transition-all duration-500 ease-out"
                  style={{
                    height: `${Math.max(heightPct, m.count > 0 ? 4 : 0)}%`,
                    background:
                      m.count > 0
                        ? "linear-gradient(to top, var(--color-brand-pink), var(--color-brand-purple))"
                        : "var(--color-bg-tertiary)",
                    minHeight: m.count > 0 ? "4px" : "2px",
                  }}
                />
              </div>
              <span className="text-[10px] text-[var(--color-text-muted)]">
                {m.label}
              </span>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-[var(--color-text-muted)] mt-4">
        Monthly premium request usage from sandbox Copilot CLI tasks.
      </p>
    </div>
  );
}
