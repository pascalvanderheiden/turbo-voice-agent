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
  IconClipboardList,
  IconHammer,
  IconRocket,
  IconTestPipe,
  IconChevronRight,
} from "@tabler/icons-react";
import { toast } from "sonner";
import Link from "next/link";
import { devApi, specsApi, skillsApi, type DevTask, type Spec, type InstalledSkill } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const STAGE_META: Record<string, { icon: typeof IconClipboardList; label: string; color: string }> = {
  plan:  { icon: IconClipboardList, label: "Plan",  color: "var(--color-brand-purple)" },
  build: { icon: IconHammer,        label: "Build", color: "var(--color-brand-cyan)" },
  run:   { icon: IconRocket,        label: "Run",   color: "var(--color-brand-pink)" },
  test:  { icon: IconTestPipe,      label: "Test",  color: "#22C55E" },
};

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
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

function StagePipeline({ stages }: { stages: DevTask["stages"] }) {
  return (
    <div className="flex items-center gap-0.5">
      {stages.map((stage, i) => {
        const meta = STAGE_META[stage.name];
        const Icon = meta?.icon || IconCode;
        const isCompleted = stage.status === "completed";
        const isRunning = stage.status === "running";
        const isFailed = stage.status === "failed";

        const ringColor = isCompleted
          ? "ring-green-500/50 bg-green-500/10"
          : isRunning
          ? "ring-blue-500/50 bg-blue-500/10 animate-pulse"
          : isFailed
          ? "ring-red-500/50 bg-red-500/10"
          : "ring-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]";

        const iconColor = isCompleted
          ? "text-green-400"
          : isRunning
          ? "text-blue-400"
          : isFailed
          ? "text-red-400"
          : "text-[var(--color-text-muted)]";

        return (
          <div key={stage.name} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-9 h-9 rounded-lg ring-1 flex items-center justify-center ${ringColor}`}
                title={`${meta?.label || stage.name}: ${stage.status}`}
              >
                {isCompleted ? (
                  <IconCircleCheck size={18} className="text-green-400" />
                ) : isFailed ? (
                  <IconCircleX size={18} className="text-red-400" />
                ) : isRunning ? (
                  <IconLoader2 size={18} className="text-blue-400 animate-spin" />
                ) : (
                  <Icon size={18} className={iconColor} />
                )}
              </div>
              <span className={`text-[10px] font-medium ${iconColor}`}>{meta?.label || stage.name}</span>
            </div>
            {i < stages.length - 1 && (
              <div className={`w-5 h-px mb-4 ${isCompleted ? "bg-green-500/40" : "bg-[var(--color-border-dark)]"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function DevelopmentPage() {
  const [tasks, setTasks] = useState<DevTask[]>([]);
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteTask, setDeleteTask] = useState<DevTask | null>(null);
  const { t } = useI18n();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const [data, specList] = await Promise.all([devApi.list(), specsApi.list().catch(() => [])]);
      setTasks(data);
      setSpecs(specList);
    } catch {
      toast.error(t("dev.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

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
      await devApi.create({ title, specId: specId || undefined, mode: mode || "mock", skillIds });
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
      toast.error("Failed to start pipeline");
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
          className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-medium bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white hover:opacity-90 transition-opacity"
        >
          <IconPlus size={16} /> {t("dev.newTask")}
        </button>
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
                    task.mode === "sequence"
                      ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                      : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                  }`}>
                    {task.mode === "sequence" ? "Sequence" : "Mock"}
                  </span>
                  {task.mode === "sequence" && task.iterations.length > 1 && (
                    <span className="text-[10px] text-[var(--color-text-muted)]">
                      {task.iterations.filter(it => it.stages.every(s => s.status === "completed")).length}/{task.iterations.length} iterations
                    </span>
                  )}
                </div>

                <StagePipeline stages={task.stages} />

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-[var(--color-border-dark)]">
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {new Date(task.createdAt).toLocaleDateString()}
                  </span>
                  <div className="flex gap-2">
                    {task.status === "pending" && (
                      <button
                        onClick={() => handleTrigger(task)}
                        className="p-1.5 rounded-[var(--radius-sm)] hover:bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] transition-colors"
                        title="Run Pipeline"
                      >
                        <IconPlayerPlay size={16} />
                      </button>
                    )}
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
    </div>
  );
}

function CreateDialog({ specs, onClose, onCreate }: { specs: Spec[]; onClose: () => void; onCreate: (title: string, specId?: string, mode?: string, skillIds?: string[]) => void }) {
  const [title, setTitle] = useState("");
  const [specId, setSpecId] = useState("");
  const [mode, setMode] = useState("mock");
  const [installedSkills, setInstalledSkills] = useState<InstalledSkill[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const { t } = useI18n();

  // Load installed skills on mount
  useEffect(() => {
    skillsApi.listInstalled().then((r) => setInstalledSkills(r.skills)).catch(() => {});
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
                onClick={() => setMode("mock")}
                className={`p-3 rounded-[var(--radius-md)] border text-sm text-left transition-all ${
                  mode === "mock"
                    ? "border-[var(--color-brand-cyan)] bg-[var(--color-brand-cyan)]/10"
                    : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                }`}
              >
                <div className="font-medium text-[var(--color-text-primary)]">Mock</div>
                <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">Quick GUI preview from full spec</div>
              </button>
              <button
                onClick={() => setMode("sequence")}
                className={`p-3 rounded-[var(--radius-md)] border text-sm text-left transition-all ${
                  mode === "sequence"
                    ? "border-[var(--color-brand-purple)] bg-[var(--color-brand-purple)]/10"
                    : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                }`}
              >
                <div className="font-medium text-[var(--color-text-primary)]">Sequence</div>
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
