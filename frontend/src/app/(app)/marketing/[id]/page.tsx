"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  IconVideo, IconPlayerPlay, IconLoader2, IconAlertCircle,
  IconCode, IconFileCode, IconArrowLeft, IconTrash, IconScript,
  IconDownload,
} from "@tabler/icons-react";
import { marketingApi, type MarketingVideo } from "@/lib/api";

export default function MarketingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [video, setVideo] = useState<MarketingVideo | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await marketingApi.get(id);
      setVideo(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh when in progress
  useEffect(() => {
    if (!video || !["pending", "scripting", "generating", "composing"].includes(video.status)) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [video, load]);

  const handleTrigger = async () => {
    if (!video) return;
    await marketingApi.trigger(video.id);
    load();
  };

  const handleDelete = async () => {
    if (!video) return;
    await marketingApi.delete(video.id);
    window.location.href = "/marketing";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <IconLoader2 size={24} className="animate-spin text-[var(--color-brand-pink)]" />
      </div>
    );
  }

  if (!video) {
    return (
      <div className="text-center py-20">
        <p className="text-[var(--color-text-muted)]">Video not found</p>
        <Link href="/marketing" className="text-[var(--color-brand-pink)] text-sm mt-2 inline-block">
          ← Back to Marketing
        </Link>
      </div>
    );
  }

  const isInProgress = ["pending", "scripting", "generating", "composing"].includes(video.status);

  const statusSteps = [
    { key: "pending", label: "Pending", icon: IconVideo },
    { key: "scripting", label: "Writing Script", icon: IconScript },
    { key: "generating", label: "Generating Video", icon: IconPlayerPlay },
    { key: "completed", label: "Completed", icon: IconVideo },
  ];

  const currentStepIdx = video.status === "failed"
    ? -1
    : statusSteps.findIndex(s => s.key === video.status);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/marketing" className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors">
          <IconArrowLeft size={18} className="text-[var(--color-text-muted)]" />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-white">{video.title}</h1>
          <div className="flex items-center gap-3 mt-1 text-xs text-[var(--color-text-muted)]">
            {video.devTaskId && (
              <Link href={`/development/${video.devTaskId}`} className="flex items-center gap-1 hover:text-[var(--color-brand-cyan)]">
                <IconCode size={12} /> Dev Task
              </Link>
            )}
            {video.specId && (
              <Link href={`/specs/${video.specId}`} className="flex items-center gap-1 hover:text-[var(--color-brand-cyan)]">
                <IconFileCode size={12} /> Spec
              </Link>
            )}
            <span>{new Date(video.createdAt).toLocaleString()}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {video.status !== "completed" && (
            <button
              onClick={handleTrigger}
              className="px-4 py-2 rounded-lg bg-[var(--color-brand-pink)] text-white text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <IconPlayerPlay size={14} />
              {video.status === "failed" ? "Retry" :
               ["scripting", "generating", "composing"].includes(video.status) ? "Restart" :
               "Generate Video"}
            </button>
          )}
          <button
            onClick={handleDelete}
            className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <IconTrash size={16} />
          </button>
        </div>
      </div>

      {/* Status Timeline */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">Generation Pipeline</h2>
        <div className="flex items-center gap-2">
          {statusSteps.map((step, i) => {
            const isDone = currentStepIdx > i;
            const isCurrent = currentStepIdx === i;
            const isFailed = video.status === "failed" && i === Math.max(0, currentStepIdx);
            return (
              <div key={step.key} className="flex items-center gap-2 flex-1">
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium flex-1 ${
                  isFailed ? "bg-red-500/10 text-red-400 border border-red-500/30" :
                  isDone ? "bg-green-500/10 text-green-400" :
                  isCurrent ? "bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] border border-[var(--color-brand-pink)]/30" :
                  "bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]"
                }`}>
                  {isCurrent && isInProgress ? (
                    <IconLoader2 size={14} className="animate-spin" />
                  ) : (
                    <step.icon size={14} />
                  )}
                  {step.label}
                </div>
                {i < statusSteps.length - 1 && (
                  <div className={`w-6 h-0.5 ${isDone ? "bg-green-500/50" : "bg-[var(--color-border-dark)]"}`} />
                )}
              </div>
            );
          })}
        </div>
        {video.status === "failed" && video.error && (
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start gap-2">
            <IconAlertCircle size={14} className="mt-0.5 shrink-0" />
            {video.error}
          </div>
        )}
      </div>

      {/* Video Player */}
      {video.status === "completed" && video.videoUrl && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden">
          <video
            controls
            className="w-full aspect-video bg-black"
            src={video.videoUrl}
          >
            Your browser does not support the video element.
          </video>
          <div className="px-4 py-2 flex items-center justify-between border-t border-[var(--color-border-dark)]">
            {video.durationSeconds ? (
              <span className="text-xs text-[var(--color-text-muted)]">
                Duration: {Math.floor(video.durationSeconds / 60)}:{(video.durationSeconds % 60).toString().padStart(2, "0")}
              </span>
            ) : <span />}
            <a
              href={video.videoUrl}
              download={`${video.title.replace(/\s+/g, "-").toLowerCase()}.mp4`}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)] hover:bg-[var(--color-brand-cyan)]/20 transition-colors"
            >
              <IconDownload size={14} />
              Download
            </a>
          </div>
        </div>
      )}

      {/* Completed but no video URL (legacy) */}
      {video.status === "completed" && !video.videoUrl && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 text-center">
          <p className="text-sm text-[var(--color-text-muted)]">Video generated but URL unavailable. Try re-triggering generation.</p>
        </div>
      )}

      {/* In-progress placeholder */}
      {isInProgress && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden">
          <div className="aspect-video bg-[var(--color-bg-tertiary)] flex flex-col items-center justify-center">
            <IconLoader2 size={40} className="animate-spin text-[var(--color-brand-cyan)] mb-4" />
            <p className="text-sm text-[var(--color-text-muted)]">
              {video.status === "scripting" ? "Writing promotional script..." :
               video.status === "generating" ? "Sora-2 is generating your video..." :
               video.status === "composing" ? "Composing final video..." :
               "Preparing to generate..."}
            </p>
          </div>
        </div>
      )}

      {/* Script */}
      {video.scriptContent && (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
          <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-4 flex items-center gap-2">
            <IconScript size={14} /> Video Script
          </h2>
          <div className="prose prose-invert prose-sm max-w-none text-[var(--color-text-secondary)] whitespace-pre-wrap">
            {video.scriptContent}
          </div>
        </div>
      )}
    </div>
  );
}
