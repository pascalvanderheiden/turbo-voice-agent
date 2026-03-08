"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  IconArrowLeft,
  IconSparkles,
  IconPencil,
  IconTrash,
  IconPlus,
  IconFileCode,
  IconLoader2,
  IconCode,
} from "@tabler/icons-react";
import { useI18n } from "@/lib/i18n";
import { specsApi, devApi, specDevApi, type Spec } from "@/lib/api";
import { toast } from "sonner";

export default function SpecDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [foundation, setFoundation] = useState<Spec | null>(null);
  const [features, setFeatures] = useState<Spec[]>([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState<string | null>(null);
  const [editSpec, setEditSpec] = useState<Spec | null>(null);
  const [deleteSpec, setDeleteSpec] = useState<Spec | null>(null);
  const [addFeature, setAddFeature] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [devTask, setDevTask] = useState<{ id: string; title: string; mode: string; status: string } | null>(null);
  const [showDevDialog, setShowDevDialog] = useState(false);
  const { t } = useI18n();

  const loadData = useCallback(async () => {
    try {
      const [spec, allSpecs] = await Promise.all([specsApi.get(id), specsApi.list()]);
      setFoundation(spec);
      setFeatures(allSpecs.filter((s) => s.parentId === id));
      // Check for linked dev task
      try {
        const dt = await specDevApi.getDevTask(id);
        setDevTask(dt.devTask);
      } catch { /* ignore */ }
    } catch {
      toast.error(t("specs.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [id, t]);

  useEffect(() => { loadData(); }, [loadData]);

  // Poll for features if none loaded yet (they may be generating in background)
  useEffect(() => {
    if (loading || features.length > 0) return;
    const interval = setInterval(async () => {
      try {
        const allSpecs = await specsApi.list();
        const newFeatures = allSpecs.filter((s) => s.parentId === id);
        if (newFeatures.length > 0) {
          setFeatures(newFeatures);
          clearInterval(interval);
        }
      } catch { /* ignore polling errors */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [loading, features.length, id]);

  const handleOptimize = async (specId: string) => {
    setOptimizing(specId);
    try {
      const updated = await specsApi.optimize(specId);
      if (updated.id === id) setFoundation(updated);
      else setFeatures((prev) => prev.map((f) => (f.id === specId ? updated : f)));
      toast.success(t("specs.optimized"));
    } catch {
      toast.error(t("specs.failed"));
    } finally {
      setOptimizing(null);
    }
  };

  const handleDelete = async (spec: Spec) => {
    try {
      await specsApi.delete(spec.id);
      toast.success(t("specs.deleted"));
      setDeleteSpec(null);
      if (spec.id === id) {
        // Deleted the foundation — go back
        router.push("/specs");
      } else {
        setFeatures((prev) => prev.filter((f) => f.id !== spec.id));
      }
    } catch {
      toast.error(t("specs.failed"));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-[var(--color-text-muted)]">
        <IconLoader2 size={20} className="animate-spin mr-2" /> {t("specs.loading")}
      </div>
    );
  }

  if (!foundation) {
    return (
      <div className="space-y-4">
        <button onClick={() => router.push("/specs")} className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
          <IconArrowLeft size={16} /> {t("specs.backToList")}
        </button>
        <p className="text-[var(--color-text-muted)]">Spec not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back */}
      <button onClick={() => router.push("/specs")} className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
        <IconArrowLeft size={16} /> {t("specs.backToList")}
      </button>

      {/* Foundation header */}
      <div>
        <h1 className="text-2xl font-semibold gradient-brand-text">{foundation.title.replace(/ — Foundation$/, "")}</h1>
        <div className="flex items-center gap-2 mt-1">
          <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-[var(--color-brand-pink)]/15 text-[var(--color-brand-pink)]">
            {t("specs.typeFoundation")}
          </span>
          <span className={`inline-block px-2 py-0.5 text-xs rounded-full ${
            foundation.status === "optimized"
              ? "bg-green-500/15 text-green-400"
              : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"
          }`}>
            {foundation.status === "optimized" ? t("specs.statusOptimized") : t("specs.statusDraft")}
          </span>
        </div>
      </div>

      {/* Foundation content */}
      <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
        <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap">
          {foundation.content || "—"}
        </div>
      </div>

      {/* Foundation actions */}
      <div className="flex gap-2 flex-wrap">
        {foundation.status === "draft" && !foundation.ideaId && (
          <button
            onClick={() => handleOptimize(foundation.id)}
            disabled={optimizing === foundation.id}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-purple)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            <IconSparkles size={16} />
            {optimizing === foundation.id ? t("specs.optimizing") : t("specs.optimize")}
          </button>
        )}
        <button
          onClick={() => setEditSpec(foundation)}
          className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <IconPencil size={16} /> {t("specs.edit")}
        </button>
        <button
          onClick={() => setDeleteSpec(foundation)}
          className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
        >
          <IconTrash size={16} /> {t("specs.delete")}
        </button>
        {!devTask && (
          <button
            onClick={() => setShowDevDialog(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <IconCode size={16} /> Develop
          </button>
        )}
        {devTask && (
          <button
            onClick={() => router.push(`/development/${devTask.id}`)}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] border border-green-500/30 bg-green-500/10 text-green-400 text-sm font-medium hover:bg-green-500/20 transition-colors"
          >
            <IconCode size={16} />
            {devTask.status === "running" ? "View Development (Running)" : devTask.status === "completed" ? "View Development (Done)" : "View Development"}
          </button>
        )}
      </div>

      {/* Features section */}
      <div className="border-t border-[var(--color-border-dark)] pt-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            Features
            {features.length > 0 && (
              <span className="ml-2 text-sm font-normal text-[var(--color-text-muted)]">({features.length})</span>
            )}
          </h2>
          <button
            onClick={() => setAddFeature(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)] text-white text-xs font-medium hover:opacity-90 transition-opacity"
          >
            <IconPlus size={14} /> Add Feature
          </button>
        </div>

        {features.length === 0 ? (
          <div className="text-center py-10 text-[var(--color-text-muted)]">
            <IconFileCode size={32} stroke={1} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">No features yet</p>
            <p className="text-xs mt-1">Features will be generated automatically or you can add them manually</p>
          </div>
        ) : (
          <div className="space-y-3">
            {features.map((feature) => {
              const isExpanded = expandedId === feature.id;
              return (
                <div key={feature.id} className="rounded-[var(--radius-lg)] bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] overflow-hidden">
                  {/* Feature header — clickable to expand */}
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : feature.id)}
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-[var(--color-bg-tertiary)]/50 transition-colors"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-[var(--color-brand-cyan)]">●</span>
                      <h3 className="font-medium text-sm truncate">{feature.title}</h3>
                      <span className={`inline-block px-2 py-0.5 text-xs rounded-full flex-shrink-0 ${
                        feature.status === "optimized"
                          ? "bg-green-500/15 text-green-400"
                          : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"
                      }`}>
                        {feature.status === "optimized" ? t("specs.statusOptimized") : t("specs.statusDraft")}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 ml-3" onClick={(e) => e.stopPropagation()}>
                      {feature.status === "draft" && !feature.ideaId && (
                        <button
                          onClick={() => handleOptimize(feature.id)}
                          disabled={optimizing === feature.id}
                          className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-brand-purple)] hover:bg-[var(--color-bg-tertiary)] transition-colors disabled:opacity-50"
                          title={t("specs.optimize")}
                        >
                          <IconSparkles size={16} />
                        </button>
                      )}
                      <button
                        onClick={() => setEditSpec(feature)}
                        className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-brand-cyan)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
                        title={t("specs.edit")}
                      >
                        <IconPencil size={16} />
                      </button>
                      <button
                        onClick={() => setDeleteSpec(feature)}
                        className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-red-400 hover:bg-[var(--color-bg-tertiary)] transition-colors"
                        title={t("specs.delete")}
                      >
                        <IconTrash size={16} />
                      </button>
                    </div>
                  </div>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="px-4 pb-4 border-t border-[var(--color-border-dark)]">
                      <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap pt-3">
                        {feature.content || "—"}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Edit Dialog */}
      {editSpec && (
        <EditDialog
          spec={editSpec}
          onClose={() => setEditSpec(null)}
          onSubmit={async (title, content) => {
            const updated = await specsApi.update(editSpec.id, { title, content });
            if (updated.id === id) setFoundation(updated);
            else setFeatures((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
            toast.success(t("specs.updated"));
            setEditSpec(null);
          }}
        />
      )}

      {/* Delete Dialog */}
      {deleteSpec && (
        <DeleteDialog
          spec={deleteSpec}
          isFoundation={deleteSpec.id === id}
          onClose={() => setDeleteSpec(null)}
          onDelete={() => handleDelete(deleteSpec)}
        />
      )}

      {/* Add Feature Dialog */}
      {addFeature && (
        <AddFeatureDialog
          onClose={() => setAddFeature(false)}
          onSubmit={async (title, content) => {
            const created = await specsApi.create({
              title,
              content,
              type: "feature",
              parentId: id,
              ideaId: foundation.ideaId || undefined,
            });
            setFeatures((prev) => [...prev, created]);
            toast.success(t("specs.created"));
            setAddFeature(false);
          }}
        />
      )}

      {/* Develop Dialog */}
      {showDevDialog && (
        <DevelopDialog
          specTitle={foundation.title}
          onClose={() => setShowDevDialog(false)}
          onSubmit={async (mode) => {
            try {
              const task = await devApi.create({ title: `Dev: ${foundation.title}`, specId: id, mode });
              try {
                await devApi.trigger(task.id, mode);
                toast.success("Development task created & pipeline started");
              } catch {
                toast.warning("Task created but pipeline failed to start. Try triggering manually.");
              }
              setShowDevDialog(false);
              router.push(`/development/${task.id}`);
            } catch {
              toast.error("Failed to create development task");
            }
          }}
        />
      )}
    </div>
  );
}

function EditDialog({
  spec,
  onClose,
  onSubmit,
}: {
  spec: Spec;
  onClose: () => void;
  onSubmit: (title: string, content: string) => Promise<void>;
}) {
  const [title, setTitle] = useState(spec.title);
  const [content, setContent] = useState(spec.content);
  const [submitting, setSubmitting] = useState(false);
  const { t } = useI18n();

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try { await onSubmit(title, content); } catch { toast.error(t("specs.failed")); } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-lg space-y-4">
        <h2 className="text-lg font-semibold">{t("specs.editDialog")}</h2>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={10}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none font-mono"
        />
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

function AddFeatureDialog({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (title: string, content: string) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { t } = useI18n();

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try { await onSubmit(title, content); } catch { toast.error(t("specs.failed")); } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-lg space-y-4">
        <h2 className="text-lg font-semibold">Add Feature</h2>
        <input
          type="text"
          placeholder="Feature title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-cyan)] transition-colors"
        />
        <textarea
          placeholder="Feature specification..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={8}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-cyan)] transition-colors resize-none font-mono"
        />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors">
            {t("specs.cancel")}
          </button>
          <button onClick={handleSubmit} disabled={submitting || !title.trim()} className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)] text-white hover:opacity-90 transition-opacity disabled:opacity-50">
            {submitting ? t("specs.saving") : t("specs.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

function DeleteDialog({
  spec,
  isFoundation,
  onClose,
  onDelete,
}: {
  spec: Spec;
  isFoundation: boolean;
  onClose: () => void;
  onDelete: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-sm space-y-4">
        <h2 className="text-lg font-semibold">{t("specs.deleteDialog")}</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {t("specs.deleteConfirm")} &ldquo;{spec.title}&rdquo;?
          {isFoundation && (
            <span className="block mt-1 text-red-400">This will delete the entire spec including all features.</span>
          )}
        </p>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors">
            {t("specs.cancel")}
          </button>
          <button onClick={onDelete} className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-red-600 text-white hover:bg-red-700 transition-colors">
            {t("specs.delete")}
          </button>
        </div>
      </div>
    </div>
  );
}

function DevelopDialog({
  specTitle,
  onClose,
  onSubmit,
}: {
  specTitle: string;
  onClose: () => void;
  onSubmit: (mode: string) => Promise<void>;
}) {
  const [mode, setMode] = useState("mock");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try { await onSubmit(mode); } catch {} finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-md space-y-4" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold">Develop: {specTitle}</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">Choose how you want to develop this spec.</p>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setMode("mock")}
            className={`p-4 rounded-[var(--radius-md)] border text-left transition-all ${
              mode === "mock" ? "border-[var(--color-brand-cyan)] bg-[var(--color-brand-cyan)]/10" : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
            }`}
          >
            <div className="font-medium">Mock</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">Quick GUI preview from full spec in one pass</div>
          </button>
          <button
            onClick={() => setMode("sequence")}
            className={`p-4 rounded-[var(--radius-md)] border text-left transition-all ${
              mode === "sequence" ? "border-[var(--color-brand-purple)] bg-[var(--color-brand-purple)]/10" : "border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
            }`}
          >
            <div className="font-medium">Sequence</div>
            <div className="text-xs text-[var(--color-text-muted)] mt-1">Iterative: foundation first, then each feature</div>
          </button>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors">
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={submitting} className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white hover:opacity-90 transition-opacity disabled:opacity-50">
            {submitting ? "Creating..." : "Start Development"}
          </button>
        </div>
      </div>
    </div>
  );
}
