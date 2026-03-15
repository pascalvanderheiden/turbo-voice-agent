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
  IconClipboardList,
  IconHammer,
  IconRocket,
  IconTestPipe,
  IconChevronDown,
  IconChevronRight,
  IconPhoto,
  IconPlus,
  IconVideo,
  IconX,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { devApi, marketingApi, type DevTask, type DevIteration, type MarketingVideo } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const STAGE_META: Record<string, { Icon: typeof IconClipboardList; label: string; color: string }> = {
  plan:  { Icon: IconClipboardList, label: "Plan",  color: "var(--color-brand-purple)" },
  build: { Icon: IconHammer,        label: "Build", color: "var(--color-brand-cyan)" },
  run:   { Icon: IconRocket,        label: "Run",   color: "var(--color-brand-pink)" },
  test:  { Icon: IconTestPipe,      label: "Test",  color: "#22C55E" },
};

function StageStatusIcon({ status }: { status: string }) {
  if (status === "completed") return <IconCircleCheck size={18} className="text-green-400" />;
  if (status === "running") return <IconLoader2 size={18} className="animate-spin text-blue-400" />;
  if (status === "failed") return <IconCircleX size={18} className="text-red-400" />;
  return <IconClock size={18} className="text-[var(--color-text-muted)]" />;
}

function IterationStages({ stages }: { stages: DevIteration["stages"] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      {stages.map((stage, i) => {
        const meta = STAGE_META[stage.name] || { Icon: IconClipboardList, label: stage.name, color: "var(--color-text-muted)" };
        const hasContent = !!(stage.output || stage.error);
        const isOpen = expanded === stage.name;
        return (
          <div key={stage.name}>
            <div
              className={`flex items-center gap-4 ${hasContent ? "cursor-pointer" : ""}`}
              onClick={() => hasContent && setExpanded(isOpen ? null : stage.name)}
            >
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center border-2 ${
                    stage.status === "completed" ? "border-green-500 bg-green-500/10"
                    : stage.status === "running" ? "border-blue-500 bg-blue-500/10"
                    : stage.status === "failed" ? "border-red-500 bg-red-500/10"
                    : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                  }`}
                >
                  {stage.status === "completed" ? <IconCircleCheck size={20} className="text-green-400" />
                  : stage.status === "running" ? <IconLoader2 size={20} className="text-blue-400 animate-spin" />
                  : stage.status === "failed" ? <IconCircleX size={20} className="text-red-400" />
                  : <meta.Icon size={20} style={{ color: meta.color }} />}
                </div>
                {i < stages.length - 1 && (
                  <div className={`w-0.5 h-4 ${stage.status === "completed" ? "bg-green-500/50" : "bg-[var(--color-border-dark)]"}`} />
                )}
              </div>
              <div className="flex-1 flex items-center gap-3">
                <span className="font-medium">{meta.label}</span>
                <StageStatusIcon status={stage.status} />
                {stage.startedAt && stage.completedAt && (
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {Math.round((new Date(stage.completedAt).getTime() - new Date(stage.startedAt).getTime()) / 1000)}s
                  </span>
                )}
                {hasContent && (
                  isOpen ? <IconChevronDown size={14} className="text-[var(--color-text-muted)]" />
                         : <IconChevronRight size={14} className="text-[var(--color-text-muted)]" />
                )}
              </div>
            </div>
            {isOpen && (
              <div className="ml-14 mt-2 mb-2">
                {stage.output && (
                  <div className={`text-xs bg-[var(--color-bg-tertiary)] rounded-[var(--radius-md)] p-3 overflow-auto max-h-80 ${
                    stage.name === "plan" ? "text-[var(--color-text-primary)] whitespace-pre-wrap leading-relaxed" : "text-[var(--color-text-secondary)] whitespace-pre-wrap font-mono"
                  }`}>
                    {stage.output}
                  </div>
                )}
                {stage.error && (
                  <pre className="text-xs text-red-400 bg-red-500/5 border border-red-500/20 rounded-[var(--radius-md)] p-3 overflow-auto max-h-64 whitespace-pre-wrap">
                    {stage.error}
                  </pre>
                )}
              </div>
            )}
          </div>
        );
      })}
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
        {(task.status === "pending" || task.status === "failed") && (
          <button onClick={handleTrigger} className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-medium bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white hover:opacity-90 transition-opacity">
            <IconPlayerPlay size={16} /> {t("dev.runPipeline")}
          </button>
        )}
        {hasArchive && (
          <a href={devApi.downloadUrl(task.id)} className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] text-sm font-medium bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors">
            <IconDownload size={16} /> {t("dev.download")}
          </a>
        )}
      </div>

      {/* Iteration tabs for openspec mode */}
      {isOpenSpec && (
        <div className="flex gap-1 overflow-x-auto pb-1">
          {iterations.map((it, i) => {
            const allDone = it.stages.every((s) => s.status === "completed");
            const anyFailed = it.stages.some((s) => s.status === "failed");
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
                    : "border-[var(--color-border-dark)] text-[var(--color-text-muted)]"
                }`}
              >
                {isCurrent && <IconLoader2 size={12} className="inline animate-spin mr-1" />}
                {it.label}
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
        <IterationStages stages={iterations[activeIteration]?.stages || task.stages} />
      </div>

      {/* Screenshots / Preview */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-4 flex items-center gap-2">
          <IconPhoto size={14} /> {t("dev.screenshots")}
        </h2>
        {screenshots.length > 0 ? (
          <div className="space-y-6">
            {/* Per-iteration screenshots (when sequence mode) */}
            {isOpenSpec && (() => {
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
            })()}

            {/* Combined gallery (always shown) */}
            {isOpenSpec && screenshots.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-[var(--color-text-secondary)] mb-3">All Screenshots</h3>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {screenshots.map((artifact, i) => (
                <div
                  key={i}
                  className="border border-[var(--color-border-dark)] rounded-[var(--radius-md)] overflow-hidden cursor-pointer hover:border-[var(--color-brand-pink)]/50 transition-colors group"
                  onClick={() => setLightboxSrc(`data:image/png;base64,${artifact.data}`)}
                >
                  <img src={`data:image/png;base64,${artifact.data}`} alt={artifact.name} className="w-full group-hover:opacity-90 transition-opacity" />
                  <div className="p-2 text-xs text-[var(--color-text-muted)] flex items-center justify-between">
                    <span>{artifact.name}{artifact.iterationIndex != null && isOpenSpec ? ` (${iterations[artifact.iterationIndex]?.label || `Iter ${artifact.iterationIndex}`})` : ""}</span>
                    <span className="text-[10px] text-[var(--color-brand-pink)]">Click to zoom</span>
                  </div>
                </div>
              ))}
            </div>
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
