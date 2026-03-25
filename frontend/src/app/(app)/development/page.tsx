"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  IconPlus,
  IconTrash,
  IconPlayerPlay,
  IconLoader2,
  IconCircleCheck,
  IconCircleX,
  IconClock,
  IconCode,
  IconSettingsAutomation,
  IconPhoto,
  IconChevronRight,
  IconSparkles,
  IconPresentation,
  IconFileExport,
  IconArchive,
  IconRocket,
} from "@tabler/icons-react";
import { toast } from "sonner";
import Link from "next/link";
import { devApi, specsApi, skillsApi, type DevTask, type Spec, type InstalledSkill, type DevIteration } from "@/lib/api";
import { sandboxApi } from "@/lib/sandbox-api";
import { useI18n } from "@/lib/i18n";
import { useIsMobile } from "@/hooks/use-is-mobile";

const STAGE_META: Record<string, { icon: typeof IconSettingsAutomation; label: string; color: string }> = {
  init:        { icon: IconSettingsAutomation, label: "Init",        color: "var(--color-brand-purple)" },
  skills:      { icon: IconCode,               label: "Skills",      color: "var(--color-brand-cyan)" },
  implement:   { icon: IconCode,               label: "Implement",   color: "var(--color-brand-cyan)" },
  screenshots: { icon: IconPhoto,              label: "Screenshots", color: "#22C55E" },
  // Slides-specific stages
  slides:      { icon: IconPresentation,       label: "Slides",      color: "var(--color-brand-cyan)" },
  run:         { icon: IconRocket,             label: "Run",         color: "#22C55E" },
  export:      { icon: IconFileExport,         label: "Export",      color: "#22C55E" },
};

function getTaskElapsed(task: DevTask): string | null {
  let earliest: number | null = null;
  let latest: number | null = null;
  for (const it of task.iterations) {
    for (const s of it.stages) {
      if (s.startedAt) {
        const t = new Date(s.startedAt).getTime();
        if (earliest === null || t < earliest) earliest = t;
      }
      if (s.completedAt) {
        const t = new Date(s.completedAt).getTime();
        if (latest === null || t > latest) latest = t;
      }
    }
  }
  if (earliest === null) return null;
  const end = latest ?? Date.now();
  const ms = end - earliest;
  if (ms < 0 || isNaN(ms)) return null;
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    paused: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    running: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    completed: "bg-green-500/10 text-green-400 border-green-500/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs border ${colors[status] || colors.pending}`}>
      {status}
    </span>
  );
}

function StagePipeline({ task }: { task: DevTask }) {
  const iterations = task.iterations.length > 0 ? task.iterations : [{ iterationIndex: 0, label: task.title, stages: task.stages, specPartId: undefined, workspacePath: undefined }];
  const foundation = iterations[0];
  const features = iterations.slice(1);

  const foundationStages = foundation?.stages.filter(s => s.name !== "screenshots") ?? [];
  const foundationDone = foundationStages.every(s => s.status === "completed");
  const foundationFailed = foundationStages.some(s => s.status === "failed");
  const foundationRunning = foundationStages.some(s => s.status === "running");

  const allFeaturesDone = features.length > 0 && features.every(f =>
    f.stages.filter(s => s.name === "implement" || s.name.startsWith("implement")).every(s => s.status === "completed")
  );

  const screenshotsStage = foundation?.stages.find(s => s.name === "screenshots");

  // Working squad members
  const workingMembers = task.squad?.teamMembers?.filter(m => m.status === "working") ?? [];
  const ROLE_EMOJI: Record<string, string> = {
    Lead: "🏗️", "Frontend Dev": "⚛️", "Backend Dev": "🔧",
    Tester: "🧪", DevOps: "🚀", Developer: "💻", Scribe: "📋",
  };

  return (
    <div className="space-y-1.5">
      {/* Foundation */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[9px] text-[var(--color-text-muted)] uppercase font-semibold w-12 shrink-0">Found.</span>
        {foundationDone ? (
          <span className="text-[10px] text-green-400 flex items-center gap-0.5"><IconCircleCheck size={12} /> Done</span>
        ) : (
          foundationStages.map((s) => {
            const color = s.status === "completed" ? "#22C55E" : s.status === "running" ? "#3B82F6" : s.status === "failed" ? "#EF4444" : "var(--color-border-dark)";
            return (
              <div key={s.name} className="w-5 h-5 rounded flex items-center justify-center border" style={{ borderColor: color }}>
                {s.status === "completed" ? <IconCircleCheck size={11} color="#4ADE80" />
                 : s.status === "running" ? <IconLoader2 size={11} color="#60A5FA" className="animate-spin" />
                 : s.status === "failed" ? <IconCircleX size={11} color="#F87171" />
                 : <div className="w-1.5 h-1.5 rounded-full bg-current opacity-30" />}
              </div>
            );
          })
        )}
      </div>

      {/* Features (compact) */}
      {features.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[9px] text-[var(--color-text-muted)] uppercase font-semibold w-12 shrink-0">Feat.</span>
          {features.map((f, i) => {
            const fDone = f.stages.filter(s => s.name === "implement" || s.name.startsWith("implement")).every(s => s.status === "completed");
            const fRunning = f.stages.some(s => s.status === "running");
            return (
              <span key={i} className={`inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[9px] border ${
                fDone ? "text-green-400 border-green-500/30" : fRunning ? "text-blue-400 border-blue-500/30" : "text-[var(--color-text-muted)] border-[var(--color-border-dark)]"
              }`}>
                {fDone ? <IconCircleCheck size={10} /> : fRunning ? <IconLoader2 size={10} className="animate-spin" /> : <IconClock size={10} />}
                {i + 1}
              </span>
            );
          })}
        </div>
      )}

      {/* Screenshots */}
      {screenshotsStage && screenshotsStage.status !== "pending" && (
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-[var(--color-text-muted)] uppercase font-semibold w-12 shrink-0">Shots</span>
          <span className={`text-[10px] flex items-center gap-0.5 ${
            screenshotsStage.status === "completed" ? "text-green-400" : screenshotsStage.status === "running" ? "text-blue-400" : "text-[var(--color-text-muted)]"
          }`}>
            {screenshotsStage.status === "completed" ? <IconCircleCheck size={12} /> : screenshotsStage.status === "running" ? <IconLoader2 size={12} className="animate-spin" /> : <IconClock size={12} />}
            {screenshotsStage.status}
          </span>
        </div>
      )}

      {/* Working squad members */}
      {(workingMembers.length > 0 || (task.status === "running" && task.squad?.teamMembers?.length)) && (
        <div className="space-y-1 pt-1">
          {workingMembers.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              {workingMembers.map((m) => (
                <span key={m.name} className="inline-flex items-center gap-0.5 text-[9px] text-[var(--color-brand-cyan)] bg-[var(--color-brand-cyan)]/5 px-1 py-0.5 rounded border border-[var(--color-brand-cyan)]/20">
                  <span>{ROLE_EMOJI[m.role] ?? "👤"}</span>
                  {m.name}
                  {m.activity && <span className="text-[var(--color-text-muted)] ml-0.5 truncate max-w-[120px]">— {m.activity}</span>}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function DevelopmentPage() {
  const [tasks, setTasks] = useState<DevTask[]>([]);
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteTask, setDeleteTask] = useState<DevTask | null>(null);
  const [archiveFilter, setArchiveFilter] = useState<"active" | "archived" | "all">("active");
  const { t } = useI18n();
  const isMobile = useIsMobile();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const archived = archiveFilter === "active" ? false : archiveFilter === "archived" ? true : undefined;
      const [data, specList] = await Promise.all([devApi.list(archived), specsApi.list().catch(() => [])]);
      setTasks(data);
      setSpecs(specList);
    } catch {
      toast.error(t("dev.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t, archiveFilter]);

  useEffect(() => { loadTasks(); }, [loadTasks]);

  // Poll for running tasks
  const hasRunning = tasks.some((t) => t.status === "running" || t.status === "pending");
  useEffect(() => {
    if (!hasRunning) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const data = await devApi.list();
        setTasks((prev) => {
          for (const task of data) {
            const old = prev.find((p) => p.id === task.id);
            if (old && old.status !== task.status) {
              if (task.status === "completed") toast.success(`${task.title} — pipeline completed!`);
              if (task.status === "failed") toast.error(`${task.title} — pipeline failed`);
            }
          }
          return data;
        });
      } catch { /* ignore */ }
    }, 3000);
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [hasRunning]);

  const handleCreate = async (title: string, specId?: string, mode?: string, skillIds?: string[]) => {
    try {
      // Check sandbox availability first
      const status = await sandboxApi.status();
      if (status.status !== "ready") {
        toast.warning("Sandbox is not running. Task will be paused until the sandbox is available.");
      }
      await devApi.create({ title, specId: specId || undefined, mode: mode || "mockup", skillIds });
      setShowCreate(false);
      loadTasks();
      toast.success(t("dev.created"));
    } catch {
      toast.error(t("dev.createFailed"));
    }
  };

  const handleDelete = async () => {
    if (!deleteTask) return;
    try {
      await devApi.delete(deleteTask.id);
      setDeleteTask(null);
      loadTasks();
    } catch {
      toast.error(t("dev.deleteFailed"));
    }
  };

  const handleTrigger = async (task: DevTask) => {
    try {
      await devApi.trigger(task.id);
      toast.success(`Pipeline started for "${task.title}"`);
      loadTasks();
    } catch {
      toast.error("Sandbox is not running. Task is paused until the sandbox is available.");
      loadTasks();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <IconLoader2 size={24} className="animate-spin text-[var(--color-brand-pink)]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{t("dev.title")}</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">{t("dev.subtitle")}</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="hidden md:flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-medium bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white hover:opacity-90 transition-opacity"
        >
          <IconPlus size={16} /> {t("dev.newTask")}
        </button>
      </div>

      {/* Archive filter tabs */}
      <div className="flex items-center gap-1 p-1 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] w-fit">
        {(["active", "archived", "all"] as const).map((filter) => (
          <button
            key={filter}
            onClick={() => setArchiveFilter(filter)}
            className={`px-3 py-1.5 text-xs rounded-[var(--radius-sm)] transition-colors ${
              archiveFilter === filter
                ? "bg-[var(--color-brand-pink)]/15 text-[var(--color-brand-pink)] font-medium"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            }`}
          >
            {filter === "active" ? "Active" : filter === "archived" ? "Archived" : "All"}
          </button>
        ))}
      </div>

      {tasks.length === 0 ? (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-12 text-center">
          <IconCode size={48} className="mx-auto text-[var(--color-text-muted)] mb-4" />
          <p className="text-[var(--color-text-muted)]">{t("dev.empty")}</p>
          <p className="text-[var(--color-text-muted)] text-sm mt-1">{t("dev.emptyHint")}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tasks.map((task) => {
            const spec = specs.find((s) => s.id === task.specId);
            // Premium requests tracked by backend per Copilot CLI invocation
            const premiumCount = task.premiumRequests ?? 0;
            return (
              <div
                key={task.id}
                className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-4 hover:border-[var(--color-brand-pink)]/30 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <Link
                    href={`/development/${task.id}`}
                    className="font-medium text-[var(--color-text-primary)] hover:text-[var(--color-brand-pink)] transition-colors line-clamp-1"
                  >
                    {task.title}
                  </Link>
                  <StatusBadge status={task.status} />
                </div>

                {spec && (
                  <p className="text-xs text-[var(--color-text-muted)] mb-2">
                    Spec: {spec.title}
                  </p>
                )}

                <div className="flex items-center gap-2 mb-3">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                    task.mode === "sequential"
                      ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                      : task.mode === "slides"
                      ? "bg-pink-500/10 text-pink-400 border-pink-500/20"
                      : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                  }`}>
                    {task.mode === "sequential" ? "Sequential" : task.mode === "slides" ? "Slidedeck" : "Mockup"}
                  </span>
                  {task.mode === "sequential" && task.iterations.length > 1 && (
                    <span className="text-[10px] text-[var(--color-text-muted)]">
                      {task.iterations.filter(it => it.stages.every(s => s.status === "completed")).length}/{task.iterations.length} iterations
                    </span>
                  )}
                  {(premiumCount > 0 || task.status === "running" || task.status === "completed") && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border bg-pink-500/10 text-[var(--color-brand-pink)] border-pink-500/20">
                      <IconSparkles size={10} stroke={1.5} />
                      {premiumCount} requests
                    </span>
                  )}
                </div>

                <StagePipeline task={task} />

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-[var(--color-border-dark)]">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {new Date(task.createdAt).toLocaleDateString()}
                    </span>
                    {getTaskElapsed(task) && (
                      <span className="text-xs text-[var(--color-text-muted)] flex items-center gap-1">
                        <IconClock size={12} />
                        {getTaskElapsed(task)}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {(task.status === "pending" || task.status === "paused") && (
                      <button
                        onClick={() => handleTrigger(task)}
                        className="p-1.5 rounded-[var(--radius-sm)] hover:bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] transition-colors"
                        title="Run Pipeline"
                      >
                        <IconPlayerPlay size={16} />
                      </button>
                    )}
                     <button
                      onClick={async (e) => {
                        e.preventDefault();
                        try {
                          if (task.archived) {
                            await devApi.unarchive(task.id);
                          } else {
                            await devApi.archive(task.id);
                          }
                          loadTasks();
                        } catch { toast.error("Failed to update archive status"); }
                      }}
                      className="p-1.5 rounded-[var(--radius-sm)] hover:bg-yellow-500/10 text-[var(--color-text-muted)] hover:text-yellow-400 transition-colors"
                      title={task.archived ? "Unarchive" : "Archive"}
                    >
                      <IconArchive size={14} />
                    </button>
                    <button
                      onClick={() => setDeleteTask(task)}
                      className="p-1.5 rounded-[var(--radius-sm)] hover:bg-red-500/10 text-[var(--color-text-muted)] hover:text-red-400 transition-colors"
                      title="Delete"
                    >
                      <IconTrash size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Dialog */}
      {showCreate && (
        <CreateDialog
          specs={specs}
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
        />
      )}

      {/* Delete Confirmation */}
      {deleteTask && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setDeleteTask(null)}>
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-medium mb-2">{t("dev.deleteConfirm")}</h3>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">"{deleteTask.title}"</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteTask(null)} className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-tertiary)]">
                {t("dev.cancel")}
              </button>
              <button onClick={handleDelete} className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-red-500/20 text-red-400 hover:bg-red-500/30">
                {t("dev.delete")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile FAB */}
      {isMobile && !showCreate && (
        <button
          onClick={() => setShowCreate(true)}
          className="fixed bottom-20 right-4 z-30 flex items-center justify-center w-14 h-14 rounded-full bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white shadow-lg shadow-[var(--color-brand-pink)]/25 hover:opacity-90 transition-opacity"
          title={t("dev.newTask")}
        >
          <IconPlus size={24} />
        </button>
      )}
    </div>
  );
}

function CreateDialog({ specs, onClose, onCreate }: { specs: Spec[]; onClose: () => void; onCreate: (title: string, specId?: string, mode?: string, skillIds?: string[]) => void }) {
  const [title, setTitle] = useState("");
  const [specId, setSpecId] = useState("");
  const [mode, setMode] = useState("mockup");
  const [installedSkills, setInstalledSkills] = useState<InstalledSkill[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const [sandboxModel, setSandboxModel] = useState("claude-opus-4.6");
  const { t } = useI18n();

  // Load installed skills and sandbox model on mount
  useEffect(() => {
    skillsApi.listInstalled().then((r) => setInstalledSkills(r.skills)).catch(() => {});
    sandboxApi.status().then((data) => {
      if (data?.config?.model) setSandboxModel(data.config.model);
    }).catch(() => {});
  }, []);

  // Auto-suggest skills when spec changes
  useEffect(() => {
    if (!specId) return;
    skillsApi.suggestForSpec(specId).then((r) => {
      if (r.skillIds?.length) {
        setSelectedSkills(new Set(r.skillIds));
      }
    }).catch(() => {});
  }, [specId]);

  const toggleSkill = (name: string) => {
    setSelectedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  // Estimate premium requests based on mode, model, and spec features
  // Each pipeline = 4 Copilot CLI calls (propose, apply, archive, screenshots)
  const premiumMultiplier = 1;
  const modelLabel = sandboxModel.replace("claude-", "").replace("gpt-", "GPT ");
  const selectedSpec = specs.find((s) => s.id === specId);
  const featureCount = selectedSpec
    ? (selectedSpec.content.match(/#### Feature:/g) || []).length
    : 0;

  const stagesPerPipeline = 4; // propose + apply + archive + screenshots
  const premiumPerPipeline = stagesPerPipeline * premiumMultiplier;
  let estimatedPremium: number;
  let estimateBreakdown: string;
  if (mode === "mockup") {
    // Mockup: 1 pipeline
    estimatedPremium = premiumPerPipeline;
    estimateBreakdown = `1 pipeline × ${stagesPerPipeline} stages × ${premiumMultiplier} = ${estimatedPremium}`;
  } else {
    // Sequential: 1 pipeline per iteration (foundation + each feature)
    const pipelineCount = 1 + featureCount;
    estimatedPremium = premiumPerPipeline * pipelineCount;
    estimateBreakdown = `${pipelineCount} pipeline${pipelineCount > 1 ? "s" : ""} × ${stagesPerPipeline} stages × ${premiumMultiplier} = ${estimatedPremium}`;
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-medium mb-4">{t("dev.newTask")}</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">{t("dev.taskTitle")}</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("dev.titlePlaceholder")}
              className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)]"
            />
          </div>
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">{t("dev.linkedSpec")}</label>
            <select
              value={specId}
              onChange={(e) => setSpecId(e.target.value)}
              className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)]"
            >
              <option value="">{t("dev.noSpec")}</option>
              {specs.filter((s) => s.type === "foundation").map((s) => (
                <option key={s.id} value={s.id}>{s.title}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Pipeline Mode</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setMode("mockup")}
                className={`p-3 rounded-[var(--radius-md)] border text-sm text-left transition-all ${
                  mode === "mockup"
                    ? "border-[var(--color-brand-cyan)] bg-[var(--color-brand-cyan)]/10"
                    : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                }`}
              >
                <div className="font-medium text-[var(--color-text-primary)]">Mockup</div>
                <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">Quick GUI preview from full spec</div>
              </button>
              <button
                onClick={() => setMode("sequential")}
                className={`p-3 rounded-[var(--radius-md)] border text-sm text-left transition-all ${
                  mode === "sequential"
                    ? "border-[var(--color-brand-purple)] bg-[var(--color-brand-purple)]/10"
                    : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                }`}
              >
                <div className="font-medium text-[var(--color-text-primary)]">Sequential</div>
                <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">Iterative: foundation → features</div>
              </button>
            </div>
          </div>
          {/* Skills Selection */}
          {installedSkills.length > 0 && (
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Skills</label>
              <p className="text-[10px] text-[var(--color-text-muted)] mb-2">Select skills to guide code generation</p>
              <div className="flex flex-wrap gap-1.5">
                {installedSkills.map((skill) => (
                  <button
                    key={skill.name}
                    onClick={() => toggleSkill(skill.name)}
                    className={`px-2.5 py-1 text-xs rounded-full border transition-all ${
                      selectedSkills.has(skill.name)
                        ? "border-[var(--color-brand-pink)] bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)]"
                        : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] hover:border-[var(--color-text-muted)]"
                    }`}
                  >
                    {skill.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {/* Premium Request Estimate */}
          <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)]">
            <div className="flex items-center gap-2 mb-1">
              <IconSparkles size={14} className="text-[var(--color-brand-pink)]" />
              <span className="text-sm font-medium text-[var(--color-text-primary)]">
                ~{estimatedPremium} premium requests
              </span>
            </div>
            <p className="text-[10px] text-[var(--color-text-muted)]">
              {estimateBreakdown} • Model: {modelLabel}
            </p>
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <button onClick={onClose} className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-tertiary)]">
              {t("dev.cancel")}
            </button>
            <button
              onClick={() => onCreate(title, specId || undefined, mode, selectedSkills.size > 0 ? [...selectedSkills] : undefined)}
              disabled={!title.trim()}
              className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white disabled:opacity-50"
            >
              {t("dev.create")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
