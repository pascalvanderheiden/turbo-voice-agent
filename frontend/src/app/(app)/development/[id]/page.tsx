"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  IconArrowLeft,
  IconLoader2,
  IconPlayerPlay,
  IconDownload,
  IconCircleCheck,
  IconCircleX,
  IconClock,
  IconSettingsAutomation,
  IconMessageChatbot,
  IconPackage,
  IconArchive,
  IconPhoto,
  IconChevronDown,
  IconChevronRight,
  IconPlus,
  IconVideo,
  IconX,
  IconTerminal2,
  IconFileCode,
  IconPuzzle,
  IconUsersGroup,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { devApi, marketingApi, type DevTask, type DevIteration, type MarketingVideo, type SquadInfo, type OpenSpecStatus, getAccessToken } from "@/lib/api";
import { sandboxApi } from "@/lib/sandbox-api";
import { useI18n } from "@/lib/i18n";

const STAGE_META: Record<string, { Icon: typeof IconSettingsAutomation; label: string; color: string }> = {
  init:        { Icon: IconSettingsAutomation, label: "Init",        color: "var(--color-brand-purple)" },
  openspec:    { Icon: IconFileCode,           label: "OpenSpec",    color: "var(--color-brand-purple)" },
  skills:      { Icon: IconPuzzle,             label: "Skills",      color: "var(--color-brand-cyan)" },
  squad:       { Icon: IconUsersGroup,         label: "Squad",       color: "var(--color-brand-pink)" },
  propose:     { Icon: IconMessageChatbot,     label: "Propose",     color: "var(--color-brand-cyan)" },
  apply:       { Icon: IconPackage,            label: "Apply",       color: "var(--color-brand-pink)" },
  archive:     { Icon: IconArchive,            label: "Archive",     color: "#F59E0B" },
  screenshots: { Icon: IconPhoto,              label: "Screenshots", color: "#22C55E" },
};

function StageStatusIcon({ status }: { status: string }) {
  if (status === "completed") return <IconCircleCheck size={18} className="text-green-400" />;
  if (status === "running") return <IconLoader2 size={18} className="animate-spin text-blue-400" />;
  if (status === "failed") return <IconCircleX size={18} className="text-red-400" />;
  return <IconClock size={18} className="text-[var(--color-text-muted)]" />;
}

/* ── Phase-based pipeline visualization ── */

const FOUNDATION_STAGES = ["init", "openspec", "skills", "squad", "propose", "apply", "archive"];
const FEATURE_STAGES = ["propose", "apply"];

const SHORT_LABELS: Record<string, string> = {
  init: "Init", openspec: "Spec", skills: "Skills", squad: "Squad",
  propose: "Prop", apply: "Apply", archive: "Arch", screenshots: "Screenshots",
};

function StageNode({ stage, meta, taskFailed }: { stage: { name: string; status: string; startedAt?: string | null; completedAt?: string | null }; meta: (typeof STAGE_META)[string]; taskFailed?: boolean }) {
  const s = taskFailed && stage.status === "running" ? "failed" : stage.status;
  const borderColor = s === "completed" ? "#22C55E" : s === "running" ? "#3B82F6" : s === "failed" ? "#EF4444" : "var(--color-border-dark)";
  const bgColor = s === "completed" ? "rgba(34,197,94,0.08)" : s === "running" ? "rgba(59,130,246,0.08)" : s === "failed" ? "rgba(239,68,68,0.08)" : "var(--color-bg-tertiary)";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center border" style={{ borderColor, backgroundColor: bgColor }}>
        {s === "completed" ? <IconCircleCheck size={18} color="#4ADE80" />
         : s === "running" ? <IconLoader2 size={18} color="#60A5FA" className="animate-spin" />
         : s === "failed" ? <IconCircleX size={18} color="#F87171" />
         : <meta.Icon size={18} style={{ color: meta.color }} />}
      </div>
      <span className="text-[10px] text-[var(--color-text-muted)] leading-tight text-center">
        {SHORT_LABELS[stage.name] ?? stage.name}
      </span>
    </div>
  );
}

function StageConnector({ completed }: { completed: boolean }) {
  return (
    <div className="flex items-center self-start mt-3.5">
      <div className="w-3 h-px" style={{ backgroundColor: completed ? "#22C55E" : "var(--color-border-dark)", opacity: 0.6 }} />
    </div>
  );
}

function PhaseBadge({ label, done, failed, running }: { label: string; done: boolean; failed?: boolean; running?: boolean }) {
  const color = done ? "text-green-400 border-green-500/30 bg-green-500/5"
    : failed ? "text-red-400 border-red-500/30 bg-red-500/5"
    : running ? "text-blue-400 border-blue-500/30 bg-blue-500/5"
    : "text-[var(--color-text-muted)] border-[var(--color-border-dark)]";
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${color}`}>
      {done ? <IconCircleCheck size={14} /> : running ? <IconLoader2 size={14} className="animate-spin" /> : failed ? <IconCircleX size={14} /> : <IconClock size={14} />}
      {label}
    </div>
  );
}

function IterationStages({ stages, taskFailed, iterations, activeIteration }: {
  stages: DevIteration["stages"];
  taskFailed?: boolean;
  iterations?: DevIteration[];
  activeIteration?: number;
}) {
  const foundation = iterations?.[0];
  const features = iterations?.slice(1) ?? [];
  const isOpenSpec = iterations && iterations.length > 0;

  // Foundation phase
  const foundationStages = isOpenSpec ? (foundation?.stages ?? []).filter(s => FOUNDATION_STAGES.includes(s.name)) : stages;
  const foundationDone = foundationStages.every(s => s.status === "completed");
  const foundationFailed = foundationStages.some(s => s.status === "failed");
  const foundationRunning = foundationStages.some(s => s.status === "running");

  // Features phase
  const allFeaturesDone = features.length > 0 && features.every(f => {
    const fStages = f.stages.filter(s => FEATURE_STAGES.includes(s.name));
    return fStages.length > 0 && fStages.every(s => s.status === "completed");
  });

  // Screenshots stage (from foundation or first iteration)
  const screenshotsStage = (foundation?.stages ?? stages).find(s => s.name === "screenshots");
  const showScreenshots = features.length === 0 || allFeaturesDone || (screenshotsStage?.status !== "pending");

  return (
    <div className="space-y-4">
      {/* Foundation phase */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wide">Foundation</span>
          {foundationDone && <PhaseBadge label="Complete" done />}
          {foundationFailed && !foundationDone && <PhaseBadge label="Failed" done={false} failed />}
        </div>
        {foundationDone ? (
          <div className="text-xs text-green-400/70 ml-1">All stages completed ✓</div>
        ) : (
          <div className="flex flex-wrap gap-1 items-start">
            {foundationStages.map((stage, i) => {
              const meta = STAGE_META[stage.name] || { Icon: IconSettingsAutomation, label: stage.name, color: "var(--color-text-muted)" };
              return (
                <div key={stage.name} className="flex items-start">
                  <StageNode stage={stage} meta={meta} taskFailed={taskFailed} />
                  {i < foundationStages.length - 1 && <StageConnector completed={stage.status === "completed"} />}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Features phase */}
      {features.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wide">Features</span>
            {allFeaturesDone && <PhaseBadge label="Complete" done />}
          </div>
          <div className="space-y-1.5">
            {features.map((feat, i) => {
              const fStages = feat.stages.filter(s => FEATURE_STAGES.includes(s.name));
              const fDone = fStages.length > 0 && fStages.every(s => s.status === "completed");
              const fFailed = fStages.some(s => s.status === "failed");
              const fRunning = fStages.some(s => s.status === "running");
              const fQueued = !foundationDone && fStages.every(s => s.status === "pending");
              return (
                <div key={i} className="flex items-center gap-3 py-1.5 px-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)]">
                  <span className="text-xs font-medium truncate flex-1 min-w-0">{feat.label}</span>
                  <div className="flex items-center gap-1 shrink-0">
                    {fQueued ? (
                      <span className="text-[10px] text-amber-400 flex items-center gap-1">
                        <IconClock size={12} /> Queued
                      </span>
                    ) : fDone ? (
                      <span className="text-[10px] text-green-400 flex items-center gap-1">
                        <IconCircleCheck size={12} /> Complete
                      </span>
                    ) : (
                      fStages.map((s) => {
                        const meta = STAGE_META[s.name] || { Icon: IconSettingsAutomation, label: s.name, color: "var(--color-text-muted)" };
                        return <StageNode key={s.name} stage={s} meta={meta} taskFailed={taskFailed} />;
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Screenshots phase */}
      {screenshotsStage && showScreenshots && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wide">Screenshots</span>
          </div>
          <StageNode
            stage={screenshotsStage}
            meta={STAGE_META.screenshots}
            taskFailed={taskFailed}
          />
        </div>
      )}
    </div>
  );
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function TerminalView({ taskId, isRunning, taskStatus }: { taskId: string; isRunning: boolean; taskStatus: string }) {
  const [lines, setLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const termRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const partialRef = useRef<string>("");

  // Connect when task is running OR was recently running (completed/failed may still have buffer data)
  const shouldConnect = isRunning || taskStatus === "completed" || taskStatus === "failed";

  useEffect(() => {
    if (!shouldConnect) {
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
      if (partialRef.current) {
        const remaining = partialRef.current;
        partialRef.current = "";
        setLines((prev) => [...prev, remaining].slice(-500));
      }
      setConnected(false);
      return;
    }

    let cancelled = false;
    const connect = async () => {
      if (cancelled || (esRef.current && esRef.current.readyState !== EventSource.CLOSED)) return;

      const token = await getAccessToken();
      const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
      const url = `${API_URL}/api/dev/${taskId}/stream${tokenParam}`;
      const es = new EventSource(url);
      esRef.current = es;
      setConnected(true);

      es.onmessage = (ev) => {
        try {
          const entry = JSON.parse(ev.data);
          if (entry.type === "stdout" || entry.type === "stderr" || entry.type === "stage" || entry.type === "decision") {
            const chunk = entry.data as string;
            const combined = partialRef.current + chunk;
            const parts = combined.split("\n");
            partialRef.current = parts.pop() ?? "";
            if (parts.length > 0) {
              setLines((prev) => [...prev, ...parts].slice(-500));
            }
          }
          if (entry.type === "exit") {
            if (partialRef.current) {
              const remaining = partialRef.current;
              partialRef.current = "";
              setLines((prev) => [...prev, remaining].slice(-500));
            }
            setConnected(false);
            es.close();
            esRef.current = null;
          }
        } catch { /* ignore parse errors */ }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        esRef.current = null;
      };
    };

    // Connect immediately on mount
    connect();
    // Retry every 5s while running
    const interval = isRunning ? setInterval(connect, 5000) : null;

    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
    };
  }, [shouldConnect, isRunning, taskId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight;
    }
  }, [lines]);

  if (taskStatus === "pending") return null;

  const emptyMessage = isRunning
    ? "Reconnecting to sandbox stream..."
    : "Waiting for sandbox output...";

  return (
    <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--color-border-dark)]">
        <div className="flex items-center gap-2">
          <IconTerminal2 size={14} className="text-[var(--color-brand-cyan)]" />
          <span className="text-xs font-medium text-[var(--color-text-muted)]">Copilot CLI Sandbox</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`relative flex h-2 w-2`}>
            {connected && <span className="absolute inset-0 rounded-full bg-green-400 opacity-75 animate-ping" />}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${connected ? "bg-green-400" : "bg-[var(--color-text-muted)]"}`} />
          </span>
          <span className="text-[10px] text-[var(--color-text-muted)]">{connected ? "Live" : lines.length > 0 ? "Disconnected" : "Waiting..."}</span>
        </div>
      </div>
      <div
        ref={termRef}
        className="p-4 font-mono text-xs leading-relaxed overflow-auto bg-[#0D0D14]"
        style={{ maxHeight: 320, minHeight: 120 }}
      >
        {lines.length === 0 ? (
          <span className="text-[var(--color-text-muted)]">
            {isRunning && <IconLoader2 size={12} className="inline animate-spin mr-1.5 align-middle" />}
            {emptyMessage}
          </span>
        ) : (
          lines.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap text-[var(--color-text-secondary)]">{line}</div>
          ))
        )}
      </div>
    </div>
  );
}

const ROLE_EMOJI: Record<string, string> = {
  Lead: "🏗️", "Frontend Dev": "⚛️", "Backend Dev": "🔧",
  Tester: "🧪", DevOps: "🚀", Developer: "💻", Scribe: "📋",
};

const STATUS_COLOR: Record<string, string> = {
  idle: "var(--color-text-muted)",
  working: "var(--color-brand-cyan)",
  done: "#22C55E",
};

function StatusPanel({ squad, openspecStatus }: { squad?: SquadInfo; openspecStatus?: OpenSpecStatus }) {
  const hasSquad = squad?.teamMembers?.length;
  const hasOpenspec = openspecStatus && openspecStatus.totalTasks > 0;
  if (!hasSquad && !hasOpenspec) return null;

  const workingMembers = squad?.teamMembers?.filter(m => m.status === "working") ?? [];
  const doneMembers = squad?.teamMembers?.filter(m => m.status === "done") ?? [];

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border-dark)] bg-[var(--color-bg-card)] p-4">
      <div className="flex gap-4 flex-col sm:flex-row">
        {/* OpenSpec status */}
        {hasOpenspec && (
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <IconFileCode size={14} className="text-purple-400 shrink-0" />
              <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">OpenSpec</span>
              {openspecStatus.changeName && (
                <span className="text-[10px] text-purple-400 truncate">{openspecStatus.changeName}</span>
              )}
            </div>
            <div className="flex items-center gap-3 mb-1.5">
              <div className="flex-1 h-1.5 rounded-full bg-[var(--color-bg-tertiary)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-purple-500 transition-all duration-500"
                  style={{ width: `${openspecStatus.totalTasks > 0 ? (openspecStatus.completedTasks / openspecStatus.totalTasks) * 100 : 0}%` }}
                />
              </div>
              <span className="text-[10px] text-[var(--color-text-muted)] shrink-0 tabular-nums">
                {openspecStatus.completedTasks}/{openspecStatus.totalTasks}
              </span>
            </div>
            <div className="flex items-center gap-3 text-[10px]">
              {openspecStatus.currentTask && (
                <span className="text-[var(--color-text-secondary)] truncate flex-1">
                  → {openspecStatus.currentTask}
                </span>
              )}
              {openspecStatus.filesChanged > 0 && (
                <span className="text-[var(--color-text-muted)] shrink-0">
                  {openspecStatus.filesChanged} files
                </span>
              )}
            </div>
          </div>
        )}

        {/* Divider */}
        {hasOpenspec && hasSquad ? <div className="hidden sm:block w-px bg-[var(--color-border-dark)]" /> : null}

        {/* Squad status */}
        {hasSquad && (
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <IconUsersGroup size={14} className="text-[var(--color-brand-pink)] shrink-0" />
              <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">Squad</span>
              <span className="text-[10px] text-[var(--color-text-muted)]">{squad!.teamMembers.length}</span>
              {workingMembers.length > 0 && (
                <span className="text-[10px] text-[var(--color-brand-cyan)]">
                  {workingMembers.length} active
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {squad!.teamMembers.map((m) => (
                <div
                  key={m.name}
                  className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-[var(--radius-md)] border text-[11px] ${
                    m.status === "working"
                      ? "border-[var(--color-brand-cyan)]/30 bg-[var(--color-brand-cyan)]/5"
                      : m.status === "done"
                      ? "border-green-500/20 bg-green-500/5"
                      : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                  }`}
                >
                  <span className="text-sm leading-none">{ROLE_EMOJI[m.role] ?? "👤"}</span>
                  <span className={`font-medium truncate max-w-[80px] ${
                    m.status === "working" ? "text-[var(--color-brand-cyan)]"
                    : m.status === "done" ? "text-green-400"
                    : "text-[var(--color-text-muted)]"
                  }`}>{m.name}</span>
                  <span
                    className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${m.status === "working" ? "animate-pulse" : ""}`}
                    style={{ backgroundColor: STATUS_COLOR[m.status] ?? STATUS_COLOR.idle }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DevTaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [task, setTask] = useState<DevTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeIteration, setActiveIteration] = useState(0);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [marketingVideos, setMarketingVideos] = useState<MarketingVideo[]>([]);
  const { t } = useI18n();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadTask = useCallback(async () => {
    try {
      const data = await devApi.get(id);
      setTask(data);
      // Load marketing videos linked to this task
      try {
        const videos = await marketingApi.listByDevTask(id);
        setMarketingVideos(videos);
      } catch { /* ignore */ }
    } catch {
      toast.error("Failed to load task");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadTask(); }, [loadTask]);

  const isRunning = task?.status === "running";
  useEffect(() => {
    if (!isRunning) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const data = await devApi.get(id);
        setTask((prev) => {
          if (prev && prev.status === "running" && data.status !== "running") {
            if (data.status === "completed") toast.success("Pipeline completed!");
            if (data.status === "failed") toast.error("Pipeline failed");
          }
          return data;
        });
      } catch { /* ignore */ }
    }, 2000);
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [isRunning, id]);

  const handleTrigger = async () => {
    if (!task) return;
    try {
      await devApi.trigger(task.id);
      toast.success("Pipeline started");
      loadTask();
    } catch {
      toast.error("Sandbox is not running. Task is paused until the sandbox is available.");
      loadTask();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <IconLoader2 size={24} className="animate-spin text-[var(--color-brand-pink)]" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="text-center py-12">
        <p className="text-[var(--color-text-muted)]">Task not found</p>
        <button onClick={() => router.push("/development")} className="mt-4 text-sm text-[var(--color-brand-pink)]">
          ← Back to Development
        </button>
      </div>
    );
  }

  const screenshots = task.artifacts.filter((a) => a.type === "screenshot" && a.name.endsWith(".png"));
  const hasArchive = task.artifacts.some((a) => a.type === "archive");
  const iterations = task.iterations.length > 0 ? task.iterations : [{ iterationIndex: 0, label: task.title, stages: task.stages, specPartId: undefined, workspacePath: undefined }];
  const isOpenSpec = task.mode === "openspec" && iterations.length > 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => router.push("/development")} className="p-2 rounded-[var(--radius-md)] hover:bg-[var(--color-bg-tertiary)] transition-colors">
          <IconArrowLeft size={18} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold truncate">{task.title}</h1>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border shrink-0 ${
              task.mode === "openspec" ? "bg-purple-500/10 text-purple-400 border-purple-500/20" : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
            }`}>
              {task.mode === "openspec" ? "OpenSpec" : "Mockup"}
            </span>
          </div>
          <p className="text-sm text-[var(--color-text-muted)]">Created {new Date(task.createdAt).toLocaleString()}</p>
          {task.skillIds && task.skillIds.length > 0 && (
            <div className="flex items-center gap-1.5 mt-1">
              <span className="text-[10px] text-[var(--color-text-muted)]">Skills:</span>
              {task.skillIds.map((s) => (
                <span key={s} className="text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] border border-[var(--color-brand-pink)]/20">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 flex-wrap">
        {(task.status === "pending" || task.status === "failed" || task.status === "paused") && (
          <button onClick={handleTrigger} className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-medium bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white hover:opacity-90 transition-opacity">
            <IconPlayerPlay size={16} /> {t("dev.runPipeline")}
          </button>
        )}
        {(task.status === "completed" || task.status === "running") && (
          <a href={devApi.downloadUrl(task.id)} className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-medium bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors">
            <IconDownload size={16} /> {t("dev.download")}
          </a>
        )}
      </div>

      {/* Paused banner */}
      {task.status === "paused" && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-[var(--radius-lg)] bg-orange-500/10 border border-orange-500/20">
          <IconClock size={18} className="text-orange-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-orange-400">Sandbox not running</p>
            <p className="text-xs text-orange-400/70 mt-0.5">
              This task is paused. Start the sandbox and click &quot;Run Pipeline&quot; to resume.
            </p>
          </div>
          <Link href="/agents" className="text-xs text-orange-400 hover:underline shrink-0">
            Go to Agents →
          </Link>
        </div>
      )}

      {/* Iteration tabs for openspec mode */}
      {isOpenSpec && (
        <div className="flex gap-1 overflow-x-auto pb-1">
          {iterations.map((it, i) => {
            const allDone = it.stages.every((s) => s.status === "completed");
            const anyFailed = it.stages.some((s) => s.status === "failed");
            const anyRunning = it.stages.some((s) => s.status === "running");
            const allPending = it.stages.every((s) => s.status === "pending");
            const foundationDone = iterations[0]?.stages.every((s) => s.status === "completed");
            const isQueued = allPending && i > 0 && !foundationDone;
            const isCurrent = task.currentIteration === i && task.status === "running";
            return (
              <button
                key={i}
                onClick={() => setActiveIteration(i)}
                className={`px-3 py-1.5 rounded-[var(--radius-md)] text-xs font-medium whitespace-nowrap border transition-all ${
                  activeIteration === i
                    ? "border-[var(--color-brand-pink)] bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)]"
                    : allDone
                    ? "border-green-500/30 bg-green-500/5 text-green-400"
                    : anyFailed
                    ? "border-red-500/30 bg-red-500/5 text-red-400"
                    : anyRunning
                    ? "border-blue-500/30 bg-blue-500/5 text-blue-400"
                    : isQueued
                    ? "border-amber-500/30 bg-amber-500/5 text-amber-400"
                    : "border-[var(--color-border-dark)] text-[var(--color-text-muted)]"
                }`}
              >
                {isCurrent && <IconLoader2 size={12} className="inline animate-spin mr-1" />}
                {isQueued && <IconClock size={12} className="inline mr-1" />}
                {it.label}
                {isQueued && <span className="ml-1 opacity-70">(queued)</span>}
              </button>
            );
          })}
        </div>
      )}

      {/* Active iteration stages */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-6">
          {isOpenSpec ? iterations[activeIteration]?.label || "Iteration" : t("dev.pipeline")}
        </h2>
        <IterationStages
          stages={iterations[activeIteration]?.stages || task.stages}
          taskFailed={task.status === "failed"}
          iterations={isOpenSpec ? iterations : undefined}
          activeIteration={activeIteration}
        />
      </div>

      {/* Squad & OpenSpec Status */}
      <StatusPanel squad={task.squad ?? undefined} openspecStatus={task.openspecStatus} />

      {/* Live Sandbox Terminal */}
      <TerminalView taskId={task.id} isRunning={task.status === "running"} taskStatus={task.status} />

      {/* Agent Decisions */}
      {task.decisions && task.decisions.length > 0 && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-4 flex items-center gap-2">
            🤖 Agent Decisions ({task.decisions.length})
          </h2>
          <div className="space-y-3">
            {task.decisions.map((d: { question: string; answer: string; stage: string; timestamp: string }, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)]">
                <span className="text-xs font-medium text-[var(--color-brand-cyan)] shrink-0 mt-0.5 w-20">{d.stage}</span>
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="text-xs text-[var(--color-text-secondary)] line-clamp-2">{d.question}</p>
                  <p className="text-xs font-medium text-green-400">→ {d.answer || "(Enter)"}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Screenshots / Preview */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-4 flex items-center gap-2">
          <IconPhoto size={14} /> {t("dev.screenshots")}
        </h2>
        {screenshots.length > 0 ? (
          <div className="space-y-6">
            {/* For openspec with multiple iterations: group by iteration */}
            {isOpenSpec ? (() => {
              const iterScreenshots = new Map<number, typeof screenshots>();
              for (const s of screenshots) {
                const idx = s.iterationIndex ?? 0;
                if (!iterScreenshots.has(idx)) iterScreenshots.set(idx, []);
                iterScreenshots.get(idx)!.push(s);
              }
              return Array.from(iterScreenshots.entries()).map(([idx, shots]) => {
                const iterLabel = iterations[idx]?.label || `Iteration ${idx}`;
                return (
                  <div key={idx}>
                    <h3 className="text-xs font-medium text-[var(--color-text-secondary)] mb-3 flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${idx === 0 ? "bg-[var(--color-brand-cyan)]" : "bg-[var(--color-brand-pink)]"}`} />
                      {iterLabel}
                      <span className="text-[var(--color-text-muted)]">· {shots.length} screenshot{shots.length !== 1 ? "s" : ""}</span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {shots.map((artifact, i) => (
                        <div
                          key={`${idx}-${i}`}
                          className="border border-[var(--color-border-dark)] rounded-[var(--radius-md)] overflow-hidden cursor-pointer hover:border-[var(--color-brand-pink)]/50 transition-colors group"
                          onClick={() => setLightboxSrc(`data:image/png;base64,${artifact.data}`)}
                        >
                          <img src={`data:image/png;base64,${artifact.data}`} alt={artifact.name} className="w-full group-hover:opacity-90 transition-opacity" />
                          <div className="p-2 text-xs text-[var(--color-text-muted)] flex items-center justify-between">
                            <span>{artifact.name}</span>
                            <span className="text-[10px] text-[var(--color-brand-pink)]">Click to zoom</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              });
            })() : (
              /* Mockup mode: single flat gallery */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {screenshots.map((artifact, i) => (
                  <div
                    key={i}
                    className="border border-[var(--color-border-dark)] rounded-[var(--radius-md)] overflow-hidden cursor-pointer hover:border-[var(--color-brand-pink)]/50 transition-colors group"
                    onClick={() => setLightboxSrc(`data:image/png;base64,${artifact.data}`)}
                  >
                    <img src={`data:image/png;base64,${artifact.data}`} alt={artifact.name} className="w-full group-hover:opacity-90 transition-opacity" />
                    <div className="p-2 text-xs text-[var(--color-text-muted)] flex items-center justify-between">
                      <span>{artifact.name}</span>
                      <span className="text-[10px] text-[var(--color-brand-pink)]">Click to zoom</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <div className="w-12 h-12 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-3">
              <IconPhoto size={20} className="text-[var(--color-text-muted)]" />
            </div>
            <p className="text-sm text-[var(--color-text-muted)]">No preview screenshots yet</p>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              {task.status === "completed"
                ? "This task completed without capturing screenshots. Re-run the pipeline to generate previews."
                : task.status === "running"
                ? "Screenshots will appear here once the test stage completes."
                : "Run the pipeline to generate application screenshots with Playwright."}
            </p>
          </div>
        )}
      </div>

      {/* Marketing Videos */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] flex items-center gap-2">
            <IconVideo size={14} /> Marketing Videos
          </h2>
          <button
            onClick={async () => {
              try {
                const video = await marketingApi.create({ title: `Promo: ${task!.title}`, devTaskId: task!.id });
                toast.success("Marketing video created");
                router.push(`/marketing/${video.id}`);
              } catch {
                toast.error("Failed to create marketing video");
              }
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white hover:opacity-90 transition-opacity"
          >
            <IconPlus size={14} /> Create Video
          </button>
        </div>
        {marketingVideos.length > 0 ? (
          <div className="space-y-3">
            {marketingVideos.map((mv) => (
              <Link
                key={mv.id}
                href={`/marketing/${mv.id}`}
                className="flex items-center gap-3 p-3 rounded-lg border border-[var(--color-border-dark)] hover:border-[var(--color-brand-pink)]/30 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-[var(--color-bg-tertiary)] flex items-center justify-center">
                  <IconVideo size={18} className={mv.status === "completed" ? "text-green-400" : "text-[var(--color-text-muted)]"} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{mv.title}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {mv.status === "completed" ? "Ready to watch" :
                     mv.status === "failed" ? "Generation failed" :
                     ["scripting", "generating", "composing"].includes(mv.status) ? "In progress..." : "Pending"}
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  mv.status === "completed" ? "bg-green-500/20 text-green-400" :
                  mv.status === "failed" ? "bg-red-500/20 text-red-400" :
                  "bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)]"
                }`}>
                  {mv.status}
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-xs text-[var(--color-text-muted)]">
            No marketing videos yet. Click &quot;Create Video&quot; to generate a promotional video for this app.
          </p>
        )}
      </div>

      {/* Lightbox */}
      {lightboxSrc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm cursor-zoom-out"
          onClick={() => setLightboxSrc(null)}
        >
          <button
            onClick={() => setLightboxSrc(null)}
            className="absolute top-4 right-4 p-2 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors"
          >
            <IconX size={20} />
          </button>
          <img
            src={lightboxSrc}
            alt="Screenshot preview"
            className="max-w-[90vw] max-h-[90vh] rounded-[var(--radius-lg)] shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
