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
  IconMessageChatbot,
  IconPackage,
  IconArchive,
  IconPhoto,
  IconChevronRight,
  IconSparkles,
} from "@tabler/icons-react";
import { toast } from "sonner";
import Link from "next/link";
import { devApi, specsApi, skillsApi, type DevTask, type Spec, type InstalledSkill } from "@/lib/api";
import { sandboxApi } from "@/lib/sandbox-api";
import { useI18n } from "@/lib/i18n";
import { useIsMobile } from "@/hooks/use-is-mobile";

const STAGE_META: Record<string, { icon: typeof IconSettingsAutomation; label: string; color: string }> = {
  init:        { icon: IconSettingsAutomation, label: "Init",        color: "var(--color-brand-purple)" },
  propose:     { icon: IconMessageChatbot,     label: "Propose",     color: "var(--color-brand-cyan)" },
  apply:       { icon: IconPackage,            label: "Apply",       color: "var(--color-brand-pink)" },
  archive:     { icon: IconArchive,            label: "Archive",     color: "#F59E0B" },
  screenshots: { icon: IconPhoto,              label: "Screenshots", color: "#22C55E" },
};

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

function StagePipeline({ stages }: { stages: DevTask["stages"] }) {
  // Layout: main row (init→archive), then screenshots drops below last stage
  const mainStages = stages.filter((s) => s.name !== "screenshots");
  const screenshotStage = stages.find((s) => s.name === "screenshots");

  // Node dimensions in viewBox units
  const nodeW = 36, nodeH = 36, gapX = 32, gapY = 44, labelH = 14;
  const mainY = 0;
  const totalMainW = mainStages.length * nodeW + (mainStages.length - 1) * gapX;
  const svgW = totalMainW + (screenshotStage ? 24 : 4);
  const svgH = screenshotStage ? mainY + nodeH + labelH + gapY + nodeH + labelH + 4 : mainY + nodeH + labelH + 4;

  const getStageColor = (status: string) => {
    if (status === "completed") return { stroke: "#22C55E", fill: "rgba(34,197,94,0.1)", text: "#4ADE80" };
    if (status === "running") return { stroke: "#3B82F6", fill: "rgba(59,130,246,0.1)", text: "#60A5FA" };
    if (status === "failed") return { stroke: "#EF4444", fill: "rgba(239,68,68,0.1)", text: "#F87171" };
    return { stroke: "var(--color-border-dark)", fill: "var(--color-bg-tertiary)", text: "var(--color-text-muted)" };
  };

  const connectorColor = (fromStatus: string) =>
    fromStatus === "completed" ? "#22C55E" : "var(--color-border-dark)";

  return (
    <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full overflow-visible" style={{ maxHeight: svgH * 1.2 }}>
      <defs>
        <marker id="arrow-green" markerWidth="4" markerHeight="4" refX="3.5" refY="2" orient="auto">
          <path d="M0,0 L4,2 L0,4" fill="none" stroke="#22C55E" strokeWidth="0.8" />
        </marker>
        <marker id="arrow-muted" markerWidth="4" markerHeight="4" refX="3.5" refY="2" orient="auto">
          <path d="M0,0 L4,2 L0,4" fill="none" stroke="var(--color-border-dark)" strokeWidth="0.8" />
        </marker>
      </defs>

      {/* Horizontal connectors between main stages */}
      {mainStages.map((stage, i) => {
        if (i >= mainStages.length - 1) return null;
        const x1 = i * (nodeW + gapX) + nodeW + 4;
        const x2 = (i + 1) * (nodeW + gapX) - 4;
        const y = mainY + nodeH / 2;
        const color = connectorColor(stage.status);
        const markerId = stage.status === "completed" ? "arrow-green" : "arrow-muted";
        return (
          <path
            key={`conn-${i}`}
            d={`M${x1},${y} C${x1 + 14},${y} ${x2 - 14},${y} ${x2},${y}`}
            stroke={color}
            strokeWidth="1.5"
            fill="none"
            opacity="0.7"
            markerEnd={`url(#${markerId})`}
          />
        );
      })}

      {/* Curved connector from right side of archive to right side of screenshots */}
      {screenshotStage && mainStages.length > 0 && (() => {
        const lastIdx = mainStages.length - 1;
        const archiveRight = lastIdx * (nodeW + gapX) + nodeW;
        const archiveMidY = mainY + nodeH / 2;
        const screenshotY = mainY + nodeH + labelH + gapY;
        const screenshotRight = archiveRight;
        const screenshotMidY = screenshotY + nodeH / 2;
        const bulge = 20;
        const color = connectorColor(mainStages[lastIdx].status);
        const markerId = mainStages[lastIdx].status === "completed" ? "arrow-green" : "arrow-muted";
        return (
          <path
            d={`M${archiveRight},${archiveMidY} C${archiveRight + bulge},${archiveMidY} ${screenshotRight + bulge},${screenshotMidY} ${screenshotRight},${screenshotMidY}`}
            stroke={color}
            strokeWidth="1.5"
            fill="none"
            opacity="0.7"
            markerEnd={`url(#${markerId})`}
          />
        );
      })()}

      {/* Main stage nodes */}
      {mainStages.map((stage, i) => {
        const x = i * (nodeW + gapX);
        const colors = getStageColor(stage.status);
        const meta = STAGE_META[stage.name];
        const cx = x + nodeW / 2, cy = mainY + nodeH / 2;
        return (
          <g key={stage.name}>
            <rect
              x={x} y={mainY} width={nodeW} height={nodeH} rx={10}
              fill={colors.fill} stroke={colors.stroke} strokeWidth="1.5"
            />
            {stage.status === "completed" ? (
              <path d={`M${cx - 6},${cy} L${cx - 1},${cy + 5} L${cx + 7},${cy - 4}`}
                stroke="#4ADE80" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            ) : stage.status === "failed" ? (
              <g stroke="#F87171" strokeWidth="2.5" strokeLinecap="round">
                <line x1={cx - 5} y1={cy - 5} x2={cx + 5} y2={cy + 5} />
                <line x1={cx + 5} y1={cy - 5} x2={cx - 5} y2={cy + 5} />
              </g>
            ) : stage.status === "running" ? (
              <circle cx={cx} cy={cy} r={6} fill="none" stroke="#60A5FA" strokeWidth="2.5"
                strokeDasharray="12 8" strokeLinecap="round">
                <animateTransform attributeName="transform" type="rotate"
                  from={`0 ${cx} ${cy}`} to={`360 ${cx} ${cy}`} dur="1s" repeatCount="indefinite" />
              </circle>
            ) : (
              <circle cx={cx} cy={cy} r={4} fill={meta?.color || "var(--color-text-muted)"} opacity="0.6" />
            )}
            <text
              x={x + nodeW / 2} y={mainY + nodeH + 12}
              textAnchor="middle" fontSize="9" fontWeight="500"
              fill={colors.text}
            >
              {meta?.label || stage.name}
            </text>
          </g>
        );
      })}

      {/* Screenshots node (below last main stage) */}
      {screenshotStage && (() => {
        const lastIdx = mainStages.length - 1;
        const x = lastIdx * (nodeW + gapX);
        const y = mainY + nodeH + labelH + gapY;
        const colors = getStageColor(screenshotStage.status);
        const meta = STAGE_META.screenshots;
        const cx = x + nodeW / 2, cy = y + nodeH / 2;
        return (
          <g>
            <rect
              x={x} y={y} width={nodeW} height={nodeH} rx={10}
              fill={colors.fill} stroke={colors.stroke} strokeWidth="1.5"
            />
            {screenshotStage.status === "completed" ? (
              <path d={`M${cx - 6},${cy} L${cx - 1},${cy + 5} L${cx + 7},${cy - 4}`}
                stroke="#4ADE80" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            ) : screenshotStage.status === "failed" ? (
              <g stroke="#F87171" strokeWidth="2.5" strokeLinecap="round">
                <line x1={cx - 5} y1={cy - 5} x2={cx + 5} y2={cy + 5} />
                <line x1={cx + 5} y1={cy - 5} x2={cx - 5} y2={cy + 5} />
              </g>
            ) : screenshotStage.status === "running" ? (
              <circle cx={cx} cy={cy} r={6} fill="none" stroke="#60A5FA" strokeWidth="2.5"
                strokeDasharray="12 8" strokeLinecap="round">
                <animateTransform attributeName="transform" type="rotate"
                  from={`0 ${cx} ${cy}`} to={`360 ${cx} ${cy}`} dur="1s" repeatCount="indefinite" />
              </circle>
            ) : (
              <circle cx={cx} cy={cy} r={4} fill={meta.color} opacity="0.6" />
            )}
            <text
              x={x + nodeW / 2} y={y + nodeH + 12}
              textAnchor="middle" fontSize="9" fontWeight="500"
              fill={colors.text}
            >
              {meta.label}
            </text>
          </g>
        );
      })()}
    </svg>
  );
}

export default function DevelopmentPage() {
  const [tasks, setTasks] = useState<DevTask[]>([]);
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteTask, setDeleteTask] = useState<DevTask | null>(null);
  const { t } = useI18n();
  const isMobile = useIsMobile();
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
            // Each completed stage = 1 premium request (Copilot CLI invocation)
            const premiumCount = task.iterations.length > 0
              ? task.iterations.reduce((sum, it) => sum + it.stages.filter((s) => s.status === "completed" || s.status === "running").length, 0)
              : task.stages.filter((s) => s.status === "completed" || s.status === "running").length;
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
                    task.mode === "openspec"
                      ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                      : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                  }`}>
                    {task.mode === "openspec" ? "OpenSpec" : "Mockup"}
                  </span>
                  {task.mode === "openspec" && task.iterations.length > 1 && (
                    <span className="text-[10px] text-[var(--color-text-muted)]">
                      {task.iterations.filter(it => it.stages.every(s => s.status === "completed")).length}/{task.iterations.length} iterations
                    </span>
                  )}
                  {premiumCount > 0 && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border bg-pink-500/10 text-[var(--color-brand-pink)] border-pink-500/20">
                      <IconSparkles size={10} stroke={1.5} />
                      {premiumCount} premium
                    </span>
                  )}
                </div>

                <StagePipeline stages={task.stages} />

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-[var(--color-border-dark)]">
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {new Date(task.createdAt).toLocaleDateString()}
                  </span>
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
                onClick={() => setMode("openspec")}
                className={`p-3 rounded-[var(--radius-md)] border text-sm text-left transition-all ${
                  mode === "openspec"
                    ? "border-[var(--color-brand-purple)] bg-[var(--color-brand-purple)]/10"
                    : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                }`}
              >
                <div className="font-medium text-[var(--color-text-primary)]">OpenSpec</div>
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
