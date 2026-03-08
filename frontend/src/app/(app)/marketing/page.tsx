"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { IconVideo, IconPlus, IconTrash, IconPlayerPlay, IconLoader2, IconAlertCircle, IconCode } from "@tabler/icons-react";
import { marketingApi, type MarketingVideo } from "@/lib/api";

export default function MarketingPage() {
  const [videos, setVideos] = useState<MarketingVideo[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await marketingApi.list();
      setVideos(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh when videos are in progress
  useEffect(() => {
    const hasInProgress = videos.some(v => ["pending", "scripting", "generating", "composing"].includes(v.status));
    if (!hasInProgress) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [videos, load]);

  const handleDelete = async (id: string) => {
    await marketingApi.delete(id);
    setVideos(prev => prev.filter(v => v.id !== id));
  };

  const statusBadge = (status: MarketingVideo["status"]) => {
    const map: Record<string, { color: string; label: string }> = {
      pending: { color: "bg-gray-500/20 text-gray-400", label: "Pending" },
      scripting: { color: "bg-blue-500/20 text-blue-400", label: "Writing Script" },
      generating: { color: "bg-purple-500/20 text-purple-400", label: "Generating Video" },
      composing: { color: "bg-cyan-500/20 text-cyan-400", label: "Composing" },
      completed: { color: "bg-green-500/20 text-green-400", label: "Completed" },
      failed: { color: "bg-red-500/20 text-red-400", label: "Failed" },
    };
    const s = map[status] || map.pending;
    return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.color}`}>{s.label}</span>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <IconVideo size={24} className="text-[var(--color-brand-pink)]" />
            Marketing Videos
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Promotional videos generated from your app screenshots using Sora-2
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <IconLoader2 size={24} className="animate-spin text-[var(--color-brand-pink)]" />
        </div>
      ) : videos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-4">
            <IconVideo size={28} className="text-[var(--color-text-muted)]" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">No marketing videos yet</h3>
          <p className="text-sm text-[var(--color-text-muted)] max-w-sm">
            Create a marketing video from a development task using voice or the dev task detail page.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map((video) => (
            <div
              key={video.id}
              className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden hover:border-[var(--color-brand-pink)]/30 transition-colors group"
            >
              {/* Thumbnail / Preview */}
              <Link href={`/marketing/${video.id}`}>
                <div className="aspect-video bg-[var(--color-bg-tertiary)] flex items-center justify-center relative">
                  {video.status === "completed" ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-12 h-12 rounded-full bg-[var(--color-brand-pink)]/80 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <IconPlayerPlay size={24} className="text-white ml-0.5" />
                      </div>
                    </div>
                  ) : video.status === "failed" ? (
                    <IconAlertCircle size={32} className="text-red-400" />
                  ) : ["scripting", "generating", "composing"].includes(video.status) ? (
                    <IconLoader2 size={32} className="animate-spin text-[var(--color-brand-cyan)]" />
                  ) : (
                    <IconVideo size={32} className="text-[var(--color-text-muted)]" />
                  )}
                </div>
              </Link>

              {/* Info */}
              <div className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <Link href={`/marketing/${video.id}`} className="flex-1">
                    <h3 className="font-medium text-white text-sm line-clamp-2 hover:text-[var(--color-brand-pink)] transition-colors">
                      {video.title}
                    </h3>
                  </Link>
                  {statusBadge(video.status)}
                </div>

                <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
                  {video.devTaskId && (
                    <Link href={`/development/${video.devTaskId}`} className="flex items-center gap-1 hover:text-[var(--color-brand-cyan)]">
                      <IconCode size={12} /> Dev Task
                    </Link>
                  )}
                  <span>{new Date(video.createdAt).toLocaleDateString()}</span>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  {video.status === "completed" && (
                    <Link
                      href={`/marketing/${video.id}`}
                      className="flex-1 text-center py-1.5 rounded-md bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] text-xs font-medium hover:bg-[var(--color-brand-pink)]/20 transition-colors"
                    >
                      Watch Video
                    </Link>
                  )}
                  <button
                    onClick={() => handleDelete(video.id)}
                    className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <IconTrash size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
