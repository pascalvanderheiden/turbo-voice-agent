"use client";

import { useCallback, useEffect, useState } from "react";
import {
  IconPlus,
  IconFileCode,
  IconSparkles,
  IconChevronRight,
  IconCode,
} from "@tabler/icons-react";
import { useI18n } from "@/lib/i18n";
import { specsApi, type Spec, type SpecCreate } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";

export default function SpecsPage() {
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const { t } = useI18n();

  const loadData = useCallback(async () => {
    try {
      const data = await specsApi.list();
      setSpecs(data);
    } catch {
      toast.error(t("specs.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { loadData(); }, [loadData]);

  // Group: foundations are top-level specs, features are children
  const foundations = specs.filter((s) => s.type === "foundation");
  const standalone = specs.filter((s) => s.type === "feature" && !s.parentId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{t("specs.title")}</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">{t("specs.subtitle")}</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <IconPlus size={16} />
          {t("specs.create")}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-text-muted)]">
          {t("specs.loading")}
        </div>
      ) : foundations.length === 0 && standalone.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-[var(--color-text-muted)]">
          <IconFileCode size={48} stroke={1} className="mb-3 opacity-50" />
          <p>{t("specs.empty")}</p>
          <p className="text-xs mt-1">{t("specs.emptyHint")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {foundations.map((foundation) => {
            const features = specs.filter((s) => s.parentId === foundation.id);
            return (
              <Link
                key={foundation.id}
                href={`/specs/${foundation.id}`}
                className="flex items-center justify-between p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] hover:border-[var(--color-brand-pink)]/30 transition-colors cursor-pointer group"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <IconFileCode size={18} className="text-[var(--color-brand-pink)] flex-shrink-0" />
                    <h3 className="font-medium text-sm truncate">{foundation.title}</h3>
                    <span className={`inline-block px-2 py-0.5 text-xs rounded-full flex-shrink-0 ${
                      foundation.status === "optimized"
                        ? "bg-green-500/15 text-green-400"
                        : foundation.status === "in-development"
                        ? "bg-blue-500/15 text-blue-400"
                        : foundation.status === "developed"
                        ? "bg-purple-500/15 text-purple-400"
                        : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"
                    }`}>
                      {foundation.status === "optimized" ? t("specs.statusOptimized")
                        : foundation.status === "in-development" ? "In Development"
                        : foundation.status === "developed" ? "Developed"
                        : t("specs.statusDraft")}
                    </span>
                    {foundation.devTaskId && (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] flex-shrink-0 cursor-pointer hover:bg-[var(--color-brand-pink)]/20 transition-colors"
                        onClick={(e) => { e.preventDefault(); window.location.href = `/development/${foundation.devTaskId}`; }}
                      >
                        <IconCode size={10} />
                        Dev Task
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1.5 truncate">
                    {foundation.content?.substring(0, 120) || "—"}
                  </p>
                  {features.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {features.map((f) => (
                        <span key={f.id} className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)] truncate max-w-[200px]">
                          {f.title}
                          {f.status === "optimized" && <IconSparkles size={10} />}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                  {features.length > 0 && (
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {features.length} feature{features.length !== 1 ? "s" : ""}
                    </span>
                  )}
                  <IconChevronRight size={16} className="text-[var(--color-text-muted)] group-hover:text-[var(--color-brand-pink)] transition-colors" />
                </div>
              </Link>
            );
          })}

          {/* Standalone feature specs (orphans without a foundation parent) */}
          {standalone.map((spec) => (
            <Link
              key={spec.id}
              href={`/specs/${spec.id}`}
              className="flex items-center justify-between p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] hover:border-[var(--color-brand-cyan)]/30 transition-colors cursor-pointer group"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <IconFileCode size={18} className="text-[var(--color-brand-cyan)] flex-shrink-0" />
                  <h3 className="font-medium text-sm truncate">{spec.title}</h3>
                  <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-[var(--color-brand-cyan)]/15 text-[var(--color-brand-cyan)]">
                    feature
                  </span>
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-1 truncate">
                  {spec.content?.substring(0, 120) || "—"}
                </p>
              </div>
              <IconChevronRight size={16} className="text-[var(--color-text-muted)] group-hover:text-[var(--color-brand-cyan)] transition-colors ml-3" />
            </Link>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      {showCreate && (
        <CreateSpecDialog
          onClose={() => setShowCreate(false)}
          onSubmit={async (title, content, optimize) => {
            const created = await specsApi.create({ title, content, type: "foundation" });
            if (optimize) {
              toast.info(t("specs.optimizing"));
              await specsApi.optimize(created.id);
              toast.success(t("specs.optimized"));
            } else {
              toast.success(t("specs.created"));
            }
            setShowCreate(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}

function CreateSpecDialog({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (title: string, content: string, optimize: boolean) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [optimize, setOptimize] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { t } = useI18n();

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try { await onSubmit(title, content, optimize); } catch { toast.error(t("specs.failed")); } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-lg space-y-4">
        <h2 className="text-lg font-semibold">{t("specs.createDialog")}</h2>
        <div className="space-y-3">
          <input
            type="text"
            placeholder={t("specs.titlePlaceholder")}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors"
          />
          <textarea
            placeholder={t("specs.contentPlaceholder")}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={8}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none font-mono"
          />
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={optimize}
              onChange={(e) => setOptimize(e.target.checked)}
              className="accent-[var(--color-brand-purple)]"
            />
            <IconSparkles size={14} className="text-[var(--color-brand-purple)]" />
            <span className="text-sm text-[var(--color-text-secondary)]">{t("specs.optimize")}</span>
          </label>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors">
            {t("specs.cancel")}
          </button>
          <button onClick={handleSubmit} disabled={submitting || !title.trim()} className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity disabled:opacity-50">
            {submitting ? t("specs.saving") : t("specs.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
