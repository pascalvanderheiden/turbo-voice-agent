"use client";

import { useEffect, useState, useCallback } from "react";
import { IconPlus, IconPencil, IconTrash, IconSparkles, IconArrowLeft, IconSearch, IconFileCode, IconLink, IconX } from "@tabler/icons-react";
import { toast } from "sonner";
import { ideasApi, researchApi, specsApi, type Idea, type Research, type Spec } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { ImageUpload } from "@/components/ui/image-upload";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { MobileBottomSheet } from "@/components/ui/mobile-bottom-sheet";

export default function IdeasPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editIdea, setEditIdea] = useState<Idea | null>(null);
  const [deleteIdea, setDeleteIdea] = useState<Idea | null>(null);
  const [viewIdea, setViewIdea] = useState<Idea | null>(null);
  const [refining, setRefining] = useState<string | null>(null);
  const [streamingDraft, setStreamingDraft] = useState<string | null>(null);
  const [linkedResearch, setLinkedResearch] = useState<Research[]>([]);
  const [linkedSpecs, setLinkedSpecs] = useState<Spec[]>([]);
  const [converting, setConverting] = useState(false);
  const { t } = useI18n();
  const isMobile = useIsMobile();

  const loadIdeas = useCallback(async () => {
    try {
      setLoading(true);
      const data = await ideasApi.list();
      setIdeas(data);
    } catch {
      toast.error(t("ideas.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadIdeas();
  }, [loadIdeas]);

  const handleRefine = async (id: string) => {
    setRefining(id);
    setStreamingDraft("");
    try {
      const fullDraft = await ideasApi.refineStream(id, (partial) => {
        setStreamingDraft(partial);
      });
      // Update with final result from backend
      const result = await ideasApi.get(id);
      toast.success(t("ideas.refined"));
      setIdeas((prev) => prev.map((i) => (i.id === id ? result : i)));
      setViewIdea(result);
    } catch {
      toast.error(t("ideas.failed"));
    } finally {
      setRefining(null);
      setStreamingDraft(null);
    }
  };

  // Mobile detail bottom sheet
  const ideaDetailContent = viewIdea && (
    <div className="space-y-4">
      <span className={`inline-block px-2 py-0.5 text-xs rounded-full ${
        viewIdea.status === "refined" ? "bg-green-500/15 text-green-400" : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"
      }`}>{viewIdea.status === "refined" ? t("ideas.statusRefined") : t("ideas.statusDraft")}</span>
      {viewIdea.description && <p className="text-sm whitespace-pre-wrap">{viewIdea.description}</p>}
      {viewIdea.refinedDraft && (
        <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-brand-pink)]/20">
          <h3 className="text-sm font-medium text-[var(--color-brand-pink)] mb-2">{t("ideas.refinedDraft")}</h3>
          <div className="text-sm whitespace-pre-wrap">{viewIdea.refinedDraft}</div>
        </div>
      )}
      {!viewIdea.refinedDraft && refining === viewIdea.id && streamingDraft && (
        <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-brand-pink)]/20">
          <h3 className="text-sm font-medium text-[var(--color-brand-pink)] mb-2 flex items-center gap-2">
            {t("ideas.refinedDraft")}
            <span className="inline-block w-2 h-4 bg-[var(--color-brand-pink)] animate-pulse rounded-sm" />
          </h3>
          <div className="text-sm whitespace-pre-wrap">{streamingDraft}</div>
        </div>
      )}
      {!viewIdea.refinedDraft && (
        <button onClick={() => handleRefine(viewIdea.id)} disabled={refining === viewIdea.id}
          className="flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] bg-[var(--color-brand-purple)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 min-h-[44px]">
          <IconSparkles size={16} /> {refining === viewIdea.id ? t("ideas.refining") : t("ideas.refine")}
        </button>
      )}
      <IdeaResearchSection ideaId={viewIdea.id} ideaTitle={viewIdea.title} ideaDescription={viewIdea.description} linkedResearch={linkedResearch} setLinkedResearch={setLinkedResearch} t={t} />
      <IdeaSpecSection ideaId={viewIdea.id} ideaTitle={viewIdea.title} linkedSpecs={linkedSpecs} setLinkedSpecs={setLinkedSpecs} converting={converting} setConverting={setConverting} t={t} />
      <div className="flex gap-2">
        <button onClick={() => { setEditIdea(viewIdea); setViewIdea(null); }}
          className="flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)] text-white text-sm font-medium hover:opacity-90 transition-opacity min-h-[44px]">
          <IconPencil size={16} /> {t("ideas.edit")}
        </button>
        <button onClick={() => setDeleteIdea(viewIdea)}
          className="flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors min-h-[44px]">
          <IconTrash size={16} /> {t("ideas.delete")}
        </button>
      </div>
    </div>
  );

  // Detail view for refined idea (desktop)
  if (!isMobile && viewIdea) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setViewIdea(null)}
          className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <IconArrowLeft size={16} /> {t("ideas.backToList")}
        </button>
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{viewIdea.title}</h1>
          <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full ${
            viewIdea.status === "refined"
              ? "bg-green-500/15 text-green-400"
              : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"
          }`}>
            {viewIdea.status === "refined" ? t("ideas.statusRefined") : t("ideas.statusDraft")}
          </span>
        </div>

        {viewIdea.description && (
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-2">{t("ideas.description")}</h3>
            <p className="text-sm whitespace-pre-wrap">{viewIdea.description}</p>
          </div>
        )}

        {viewIdea.refinedDraft && (
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-brand-pink)]/20">
            <h3 className="text-sm font-medium text-[var(--color-brand-pink)] mb-2">{t("ideas.refinedDraft")}</h3>
            <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap">
              {viewIdea.refinedDraft}
            </div>
          </div>
        )}

        {!viewIdea.refinedDraft && refining === viewIdea.id && streamingDraft && (
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-brand-pink)]/20">
            <h3 className="text-sm font-medium text-[var(--color-brand-pink)] mb-2 flex items-center gap-2">
              {t("ideas.refinedDraft")}
              <span className="inline-block w-2 h-4 bg-[var(--color-brand-pink)] animate-pulse rounded-sm" />
            </h3>
            <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap">
              {streamingDraft}
            </div>
          </div>
        )}

        {!viewIdea.refinedDraft && (
          <button
            onClick={() => handleRefine(viewIdea.id)}
            disabled={refining === viewIdea.id}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-purple)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            <IconSparkles size={16} />
            {refining === viewIdea.id ? t("ideas.refining") : t("ideas.refine")}
          </button>
        )}

        {/* Linked Research */}
        <IdeaResearchSection ideaId={viewIdea.id} ideaTitle={viewIdea.title} ideaDescription={viewIdea.description} linkedResearch={linkedResearch} setLinkedResearch={setLinkedResearch} t={t} />

        {/* Linked Specs / Convert to Spec */}
        <IdeaSpecSection ideaId={viewIdea.id} ideaTitle={viewIdea.title} linkedSpecs={linkedSpecs} setLinkedSpecs={setLinkedSpecs} converting={converting} setConverting={setConverting} t={t} />

        <div className="flex gap-2">
          <button
            onClick={() => { setEditIdea(viewIdea); setViewIdea(null); }}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <IconPencil size={16} /> {t("ideas.edit")}
          </button>
          <button
            onClick={() => setDeleteIdea(viewIdea)}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
          >
            <IconTrash size={16} /> {t("ideas.delete")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Mobile detail bottom sheet */}
      {isMobile && viewIdea && (
        <MobileBottomSheet open={!!viewIdea} onClose={() => setViewIdea(null)} title={viewIdea.title}>
          {ideaDetailContent}
        </MobileBottomSheet>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{t("ideas.title")}</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">{t("ideas.subtitle")}</p>
        </div>
        {!isMobile && (
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <IconPlus size={16} />
          {t("ideas.create")}
        </button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-text-muted)]">
          {t("ideas.loading")}
        </div>
      ) : ideas.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-[var(--color-text-muted)]">
          <p>{t("ideas.empty")}</p>
          <p className="text-xs mt-1">{t("ideas.emptyHint")}</p>
        </div>
      ) : (
        isMobile ? (
          <div className="space-y-2">
            {ideas.map((idea) => (
              <button
                key={idea.id}
                onClick={() => setViewIdea(idea)}
                className="w-full text-left p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] min-h-[44px] active:bg-[var(--color-bg-tertiary)] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <p className="font-medium text-sm flex-1">{idea.title}</p>
                  <span className={`px-2 py-0.5 text-[10px] rounded-full flex-shrink-0 ${idea.status === "refined" ? "bg-green-500/15 text-green-400" : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"}`}>
                    {idea.status === "refined" ? t("ideas.statusRefined") : t("ideas.statusDraft")}
                  </span>
                </div>
                {idea.description && <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{idea.description}</p>}
              </button>
            ))}
          </div>
        ) : (
        <div className="border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] text-left">
                <th className="px-4 py-3 font-medium">{t("ideas.colTitle")}</th>
                <th className="px-4 py-3 font-medium hidden md:table-cell">{t("ideas.colStatus")}</th>
                <th className="px-4 py-3 font-medium hidden md:table-cell">{t("ideas.colImages")}</th>
                <th className="px-4 py-3 font-medium hidden lg:table-cell">{t("ideas.colUpdated")}</th>
                <th className="px-4 py-3 font-medium w-32">{t("ideas.colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {ideas.map((idea) => (
                <tr
                  key={idea.id}
                  className="border-t border-[var(--color-border-dark)] hover:bg-[var(--color-bg-secondary)] transition-colors cursor-pointer"
                  onClick={() => setViewIdea(idea)}
                >
                  <td className="px-4 py-3 font-medium">{idea.title}</td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      idea.status === "refined"
                        ? "bg-green-500/15 text-green-400"
                        : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"
                    }`}>
                      {idea.status === "refined" ? t("ideas.statusRefined") : t("ideas.statusDraft")}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell text-[var(--color-text-muted)]">
                    {idea.images?.length || 0}
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-muted)] hidden lg:table-cell">
                    {new Date(idea.updatedAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleRefine(idea.id)}
                        disabled={refining === idea.id}
                        className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-brand-purple)] hover:bg-[var(--color-bg-tertiary)] transition-colors disabled:opacity-50"
                        title={t("ideas.refine")}
                      >
                        <IconSparkles size={16} />
                      </button>
                      <button
                        onClick={() => setEditIdea(idea)}
                        className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-brand-cyan)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
                        title={t("ideas.edit")}
                      >
                        <IconPencil size={16} />
                      </button>
                      <button
                        onClick={() => setDeleteIdea(idea)}
                        className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-red-400 hover:bg-[var(--color-bg-tertiary)] transition-colors"
                        title={t("ideas.delete")}
                      >
                        <IconTrash size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )
      )}

      {/* Create Dialog */}
      {showCreate && (
        isMobile ? (
          <MobileBottomSheet open={showCreate} onClose={() => setShowCreate(false)} title={t("ideas.createDialog")}>
            <IdeaForm
              onSubmit={async (title, description, images) => {
                await ideasApi.create({ title, description, images });
                toast.success(t("ideas.created"));
                setShowCreate(false);
                loadIdeas();
              }}
            />
          </MobileBottomSheet>
        ) : (
        <IdeaDialog
          onClose={() => setShowCreate(false)}
          onSubmit={async (title, description, images) => {
            await ideasApi.create({ title, description, images });
            toast.success(t("ideas.created"));
            setShowCreate(false);
            loadIdeas();
          }}
        />
        )
      )}

      {/* Edit Dialog */}
      {editIdea && (
        isMobile ? (
          <MobileBottomSheet open={!!editIdea} onClose={() => setEditIdea(null)} title={t("ideas.editDialog")}>
            <IdeaForm
              initialTitle={editIdea.title}
              initialDescription={editIdea.description}
              initialImages={editIdea.images}
              onSubmit={async (title, description, images) => {
                await ideasApi.update(editIdea.id, { title, description, images });
                toast.success(t("ideas.updated"));
                setEditIdea(null);
                loadIdeas();
              }}
            />
          </MobileBottomSheet>
        ) : (
        <IdeaDialog
          initialTitle={editIdea.title}
          initialDescription={editIdea.description}
          initialImages={editIdea.images}
          onClose={() => setEditIdea(null)}
          onSubmit={async (title, description, images) => {
            await ideasApi.update(editIdea.id, { title, description, images });
            toast.success(t("ideas.updated"));
            setEditIdea(null);
            loadIdeas();
          }}
        />
        )
      )}

      {/* Delete Dialog */}
      {deleteIdea && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-sm space-y-4">
            <h2 className="text-lg font-semibold">{t("ideas.deleteDialog")}</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {t("ideas.deleteConfirm")} &ldquo;{deleteIdea.title}&rdquo;? {t("ideas.deleteWarning")}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteIdea(null)}
                className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
              >
                {t("ideas.cancel")}
              </button>
              <button
                onClick={async () => {
                  await ideasApi.delete(deleteIdea.id);
                  toast.success(t("ideas.deleted"));
                  setDeleteIdea(null);
                  loadIdeas();
                }}
                className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                {t("ideas.delete")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile FAB */}
      {isMobile && !showCreate && !editIdea && !viewIdea && (
        <button
          onClick={() => setShowCreate(true)}
          className="fixed bottom-20 right-4 z-30 flex items-center justify-center w-14 h-14 rounded-full bg-[var(--color-brand-pink)] text-white shadow-lg shadow-[var(--color-brand-pink)]/25 hover:opacity-90 transition-opacity"
          title={t("ideas.create")}
        >
          <IconPlus size={24} />
        </button>
      )}
    </div>
  );
}

function IdeaForm({
  initialTitle = "",
  initialDescription = "",
  initialImages = [],
  onSubmit,
}: {
  initialTitle?: string;
  initialDescription?: string;
  initialImages?: string[];
  onSubmit: (title: string, description: string, images: string[]) => Promise<void>;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [images, setImages] = useState<string[]>(initialImages);
  const [submitting, setSubmitting] = useState(false);
  const { t } = useI18n();

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try { await onSubmit(title, description, images); }
    catch { toast.error(t("ideas.failed")); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="space-y-4">
      <input type="text" placeholder={t("ideas.titlePlaceholder")} value={title} onChange={(e) => setTitle(e.target.value)}
        className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors min-h-[44px]" />
      <textarea placeholder={t("ideas.descriptionPlaceholder")} value={description} onChange={(e) => setDescription(e.target.value)} rows={4}
        className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none" />
      <ImageUpload images={images} onChange={setImages} />
      <button onClick={handleSubmit} disabled={submitting || !title.trim()}
        className="w-full px-4 py-3 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 min-h-[44px]">
        {submitting ? t("ideas.saving") : t("ideas.save")}
      </button>
    </div>
  );
}

function IdeaDialog({
  initialTitle = "",
  initialDescription = "",
  initialImages = [],
  onClose,
  onSubmit,
}: {
  initialTitle?: string;
  initialDescription?: string;
  initialImages?: string[];
  onClose: () => void;
  onSubmit: (title: string, description: string, images: string[]) => Promise<void>;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [images, setImages] = useState<string[]>(initialImages);
  const [submitting, setSubmitting] = useState(false);
  const { t } = useI18n();
  const isEdit = !!initialTitle;

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(title, description, images);
    } catch {
      toast.error(t("ideas.failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-lg space-y-4">
        <h2 className="text-lg font-semibold">{isEdit ? t("ideas.editDialog") : t("ideas.createDialog")}</h2>
        <div className="space-y-3">
          <input
            type="text"
            placeholder={t("ideas.titlePlaceholder")}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors"
          />
          <textarea
            placeholder={t("ideas.descriptionPlaceholder")}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none"
          />
          <ImageUpload images={images} onChange={setImages} />
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
          >
            {t("ideas.cancel")}
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !title.trim()}
            className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {submitting ? t("ideas.saving") : t("ideas.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

function IdeaResearchSection({
  ideaId,
  ideaTitle,
  ideaDescription,
  linkedResearch,
  setLinkedResearch,
  t,
}: {
  ideaId: string;
  ideaTitle: string;
  ideaDescription: string;
  linkedResearch: Research[];
  setLinkedResearch: React.Dispatch<React.SetStateAction<Research[]>>;
  t: (k: string) => string;
}) {
  const [searching, setSearching] = useState(false);
  const [showLinkPicker, setShowLinkPicker] = useState(false);
  const [allResearch, setAllResearch] = useState<Research[]>([]);
  const [loadingLink, setLoadingLink] = useState(false);

  useEffect(() => {
    researchApi.listByIdea(ideaId).then(setLinkedResearch).catch(() => {});
    // Poll every 5s for background completions
    const interval = setInterval(() => {
      researchApi.listByIdea(ideaId).then(setLinkedResearch).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [ideaId, setLinkedResearch]);

  const handleResearch = async () => {
    setSearching(true);
    try {
      const query = `${ideaTitle}${ideaDescription ? `: ${ideaDescription}` : ""}`;
      const result = await researchApi.webSearch(query, ideaId);
      setLinkedResearch((prev) => [result, ...prev]);
      toast.success(t("research.created"));
    } catch {
      toast.error(t("research.failed"));
    } finally {
      setSearching(false);
    }
  };

  const handleOpenLinkPicker = async () => {
    try {
      const all = await researchApi.list();
      setAllResearch(all);
      setShowLinkPicker(true);
    } catch {
      toast.error("Failed to load research");
    }
  };

  const handleLinkResearch = async (researchId: string) => {
    setLoadingLink(true);
    try {
      const updated = await researchApi.linkToIdea(researchId, ideaId);
      setLinkedResearch((prev) => [updated, ...prev]);
      setAllResearch((prev) => prev.filter((r) => r.id !== researchId));
      toast.success("Research linked to idea");
    } catch {
      toast.error("Failed to link research");
    } finally {
      setLoadingLink(false);
    }
  };

  const handleUnlinkResearch = async (researchId: string) => {
    try {
      await researchApi.unlinkFromIdea(researchId);
      setLinkedResearch((prev) => prev.filter((r) => r.id !== researchId));
      toast.success("Research unlinked");
    } catch {
      toast.error("Failed to unlink research");
    }
  };

  const linkedIds = new Set(linkedResearch.map((r) => r.id));
  const unlinkableResearch = allResearch.filter((r) => !linkedIds.has(r.id) && r.status === "completed");

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">{t("research.linkedResearch")}</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleOpenLinkPicker}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)] text-xs bg-[var(--color-brand-purple)]/10 text-[var(--color-brand-purple)] hover:bg-[var(--color-brand-purple)]/20"
          >
            <IconLink size={14} /> {t("research.linkExisting") || "Link Existing"}
          </button>
          <button
            onClick={handleResearch}
            disabled={searching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)] text-xs bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)] hover:bg-[var(--color-brand-cyan)]/20 disabled:opacity-50"
          >
            <IconSearch size={14} /> {searching ? t("research.searching") : t("research.researchIdea")}
          </button>
        </div>
      </div>

      {/* Link picker dropdown */}
      {showLinkPicker && (
        <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[var(--color-text-secondary)]">
              {t("research.selectToLink") || "Select research to link"}
            </span>
            <button onClick={() => setShowLinkPicker(false)} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
              <IconX size={14} />
            </button>
          </div>
          {unlinkableResearch.length === 0 ? (
            <p className="text-xs text-[var(--color-text-muted)]">
              {t("research.noUnlinked") || "No completed research available to link"}
            </p>
          ) : (
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {unlinkableResearch.map((r) => (
                <button
                  key={r.id}
                  onClick={() => handleLinkResearch(r.id)}
                  disabled={loadingLink}
                  className="w-full text-left p-2 rounded-[var(--radius-sm)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-brand-purple)]/10 text-sm disabled:opacity-50"
                >
                  <div className="font-medium truncate">{r.title}</div>
                  <div className="text-xs text-[var(--color-text-muted)]">
                    {r.mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch")}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {linkedResearch.length > 0 && (
        <div className="space-y-2">
          {linkedResearch.map((r) => (
            <div
              key={r.id}
              className="flex items-center gap-2 p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] hover:border-[var(--color-brand-cyan)]/30 text-sm"
            >
              <a href="/research" className="flex-1 min-w-0">
                <div className="font-medium truncate">{r.title}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {r.mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch")} · {r.status === "completed" ? t("research.statusCompleted") : r.status === "failed" ? t("research.statusFailed") : t("research.statusPending")}
                </div>
              </a>
              <button
                onClick={(e) => { e.preventDefault(); handleUnlinkResearch(r.id); }}
                className="shrink-0 p-1 rounded text-[var(--color-text-muted)] hover:text-red-400 hover:bg-red-400/10"
                title={t("research.unlink") || "Unlink"}
              >
                <IconX size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function IdeaSpecSection({
  ideaId,
  ideaTitle,
  linkedSpecs,
  setLinkedSpecs,
  converting,
  setConverting,
  t,
}: {
  ideaId: string;
  ideaTitle: string;
  linkedSpecs: Spec[];
  setLinkedSpecs: React.Dispatch<React.SetStateAction<Spec[]>>;
  converting: boolean;
  setConverting: React.Dispatch<React.SetStateAction<boolean>>;
  t: (k: string) => string;
}) {
  useEffect(() => {
    specsApi.list().then((all) => {
      setLinkedSpecs(all.filter((s) => s.ideaId === ideaId));
    }).catch(() => {});
    // Poll every 5s for background completions
    const interval = setInterval(() => {
      specsApi.list().then((all) => {
        setLinkedSpecs(all.filter((s) => s.ideaId === ideaId));
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [ideaId, setLinkedSpecs]);

  const handleConvert = async () => {
    setConverting(true);
    try {
      await specsApi.generate(ideaId);
      const all = await specsApi.list();
      setLinkedSpecs(all.filter((s) => s.ideaId === ideaId));
      toast.success(t("specs.generated"));
    } catch {
      toast.error(t("specs.failed"));
    } finally {
      setConverting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">{t("specs.linkedSpecs")}</h3>
        <button
          onClick={handleConvert}
          disabled={converting}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)] text-xs bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] hover:bg-[var(--color-brand-pink)]/20 disabled:opacity-50"
        >
          <IconFileCode size={14} /> {converting ? t("specs.converting") : t("specs.convertToSpec")}
        </button>
      </div>
      {linkedSpecs.filter((s) => s.type === "foundation").length > 0 && (
        <div className="space-y-2">
          {linkedSpecs.filter((s) => s.type === "foundation").map((s) => (
            <a
              key={s.id}
              href={`/specs/${s.id}`}
              className="block p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] hover:border-[var(--color-brand-pink)]/30 text-sm"
            >
              <div className="font-medium">{s.title.replace(/ — Foundation$/, "")}</div>
              <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                {t("specs.typeFoundation")} · {s.status === "optimized" ? t("specs.statusOptimized") : s.status === "in-development" ? "In Development" : s.status === "developed" ? "Developed" : t("specs.statusDraft")}
                {linkedSpecs.filter((f) => f.parentId === s.id).length > 0 && (
                  <span> · {linkedSpecs.filter((f) => f.parentId === s.id).length} feature{linkedSpecs.filter((f) => f.parentId === s.id).length !== 1 ? "s" : ""}</span>
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
