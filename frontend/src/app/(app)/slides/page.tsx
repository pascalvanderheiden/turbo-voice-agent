"use client";

import { useEffect, useState, useCallback } from "react";
import { IconPlus, IconPencil, IconTrash, IconSparkles, IconArrowLeft, IconPresentation, IconX, IconPlayerPlay } from "@tabler/icons-react";
import { toast } from "sonner";
import { slidesApi, devApi, getUploadUrl, type SlidesItem, type SlidesCreate, type Research } from "@/lib/api";
import { ImageUpload } from "@/components/ui/image-upload";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { MobileBottomSheet } from "@/components/ui/mobile-bottom-sheet";

export default function SlidesPage() {
  const [slides, setSlides] = useState<SlidesItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editSlides, setEditSlides] = useState<SlidesItem | null>(null);
  const [deleteSlides, setDeleteSlides] = useState<SlidesItem | null>(null);
  const [viewSlides, setViewSlides] = useState<SlidesItem | null>(null);
  const [refining, setRefining] = useState<string | null>(null);
  const [streamingDraft, setStreamingDraft] = useState<string | null>(null);
  const [linkedResearch, setLinkedResearch] = useState<Research[]>([]);
  const [developing, setDeveloping] = useState(false);
  const isMobile = useIsMobile();

  const loadSlides = useCallback(async () => {
    try {
      const data = await slidesApi.list();
      setSlides(data);
    } catch {
      toast.error("Failed to load presentations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSlides();
  }, [loadSlides]);

  const handleRefine = async (id: string) => {
    setRefining(id);
    setStreamingDraft("");
    try {
      await slidesApi.refineStream(id, (partial) => {
        setStreamingDraft(partial);
      });
      const result = await slidesApi.get(id);
      toast.success("Presentation refined successfully");
      setSlides((prev) => prev.map((s) => (s.id === id ? result : s)));
      setViewSlides(result);
    } catch {
      toast.error("Refinement failed");
    } finally {
      setRefining(null);
      setStreamingDraft(null);
    }
  };

  const handleDetailFilesChange = async (item: SlidesItem, attachments: string[]) => {
    try {
      const updated = await slidesApi.update(item.id, { attachments });
      setSlides((prev) => prev.map((s) => (s.id === item.id ? updated : s)));
      setViewSlides(updated);
    } catch {
      toast.error("Failed to update files");
    }
  };

  const handleDevelop = async (item: SlidesItem) => {
    setDeveloping(true);
    try {
      const task = await devApi.create({
        title: `Slidedeck: ${item.title}`,
        slidesId: item.id,
        mode: "slides",
      });
      await devApi.trigger(task.id, "slides");
      toast.success("Slidedeck development started");
      window.location.href = `/development/${task.id}`;
    } catch {
      toast.error("Failed to start slidedeck development");
    } finally {
      setDeveloping(false);
    }
  };

  // Load linked research when viewing
  useEffect(() => {
    if (viewSlides) {
      slidesApi.listResearch(viewSlides.id).then(setLinkedResearch).catch(() => setLinkedResearch([]));
    } else {
      setLinkedResearch([]);
    }
  }, [viewSlides?.id]);

  const slidesDetailContent = viewSlides ? (
    <div className="space-y-4 p-4">
      {/* Status badge */}
      <div className="flex items-center gap-2">
        <span className={`px-2 py-0.5 text-[10px] rounded-full ${viewSlides.status === "refined" ? "bg-green-500/15 text-green-400" : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"}`}>
          {viewSlides.status === "refined" ? "Refined" : "Draft"}
        </span>
        {viewSlides.sections.length > 0 && (
          <span className="text-xs text-[var(--color-text-muted)]">{viewSlides.sections.length} slides</span>
        )}
      </div>

      {/* Description */}
      {viewSlides.description && (
        <div className="p-3 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
          <p className="text-sm whitespace-pre-wrap">{viewSlides.description}</p>
        </div>
      )}

      {/* Files section */}
      <SlidesFilesSection slides={viewSlides} onFilesChange={handleDetailFilesChange} />

      {/* Streaming refinement */}
      {refining === viewSlides.id && streamingDraft && (
        <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-brand-pink)]/20">
          <h3 className="text-sm font-medium text-[var(--color-brand-pink)] mb-2 flex items-center gap-2">
            Refined Draft
            <span className="inline-block w-2 h-4 bg-[var(--color-brand-pink)] animate-pulse rounded-sm" />
          </h3>
          <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap">{streamingDraft}</div>
        </div>
      )}

      {/* Existing refined draft */}
      {viewSlides.refinedDraft && refining !== viewSlides.id && (
        <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-2">Refined Draft</h3>
          <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap">{viewSlides.refinedDraft}</div>
        </div>
      )}

      {/* Research section */}
      {linkedResearch.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Linked Research</h3>
          {linkedResearch.map((r) => (
            <div key={r.id} className="p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm">
              <p className="font-medium">{r.title}</p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">{r.status}</p>
            </div>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 pt-2">
        <button
          onClick={() => handleRefine(viewSlides.id)}
          disabled={refining === viewSlides.id}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] hover:bg-[var(--color-brand-pink)]/20 transition-colors disabled:opacity-50 min-h-[44px]"
        >
          <IconSparkles size={16} />
          {refining === viewSlides.id ? "Refining..." : viewSlides.status === "refined" ? "Re-refine" : "Refine"}
        </button>
        {viewSlides.status === "refined" && (
          <button
            onClick={() => handleDevelop(viewSlides)}
            disabled={developing}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)] hover:bg-[var(--color-brand-cyan)]/20 transition-colors disabled:opacity-50 min-h-[44px]"
          >
            <IconPlayerPlay size={16} />
            {developing ? "Starting..." : "Develop"}
          </button>
        )}
        <button
          onClick={() => { setEditSlides(viewSlides); }}
          className="px-4 py-3 text-sm rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-white transition-colors min-h-[44px]"
        >
          <IconPencil size={16} />
        </button>
        <button
          onClick={() => { setDeleteSlides(viewSlides); }}
          className="px-4 py-3 text-sm rounded-[var(--radius-md)] bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors min-h-[44px]"
        >
          <IconTrash size={16} />
        </button>
      </div>
    </div>
  ) : null;

  // If viewing detail on desktop
  if (viewSlides && !isMobile) {
    return (
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <button onClick={() => setViewSlides(null)} className="flex items-center gap-1 text-sm text-[var(--color-text-muted)] hover:text-white transition-colors">
          <IconArrowLeft size={16} /> Back to presentations
        </button>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{viewSlides.title}</h1>
          <span className={`px-3 py-1 text-xs rounded-full ${viewSlides.status === "refined" ? "bg-green-500/15 text-green-400" : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"}`}>
            {viewSlides.status === "refined" ? "Refined" : "Draft"}
          </span>
        </div>

        {/* Description */}
        {viewSlides.description && (
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-2">Description</h3>
            <p className="text-sm whitespace-pre-wrap">{viewSlides.description}</p>
          </div>
        )}

        {/* Files */}
        <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-3">Files & Attachments</h3>
          <SlidesFilesSection slides={viewSlides} onFilesChange={handleDetailFilesChange} />
        </div>

        {/* Streaming refinement */}
        {refining === viewSlides.id && streamingDraft && (
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-brand-pink)]/20">
            <h3 className="text-sm font-medium text-[var(--color-brand-pink)] mb-2 flex items-center gap-2">
              Refined Draft
              <span className="inline-block w-2 h-4 bg-[var(--color-brand-pink)] animate-pulse rounded-sm" />
            </h3>
            <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap">{streamingDraft}</div>
          </div>
        )}

        {/* Existing refined draft */}
        {viewSlides.refinedDraft && refining !== viewSlides.id && (
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-2">Refined Draft</h3>
            <div className="text-sm prose prose-invert max-w-none whitespace-pre-wrap">{viewSlides.refinedDraft}</div>
          </div>
        )}

        {/* Sections preview */}
        {viewSlides.sections.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Slide Sections ({viewSlides.sections.length})</h3>
            {viewSlides.sections.map((section, i) => (
              <div key={i} className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs text-[var(--color-text-muted)] bg-[var(--color-bg-tertiary)] px-2 py-0.5 rounded">Slide {i + 1}</span>
                  <h4 className="text-sm font-medium">{section.title || "Untitled Slide"}</h4>
                </div>
                {section.content && <p className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap">{section.content}</p>}
                {section.notes && <p className="text-xs text-[var(--color-text-muted)] mt-2 italic">Notes: {section.notes}</p>}
              </div>
            ))}
          </div>
        )}

        {/* Research */}
        {linkedResearch.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Linked Research</h3>
            {linkedResearch.map((r) => (
              <div key={r.id} className="p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm">
                <p className="font-medium">{r.title}</p>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">{r.status}</p>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => handleRefine(viewSlides.id)}
            disabled={refining === viewSlides.id}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] hover:bg-[var(--color-brand-pink)]/20 transition-colors disabled:opacity-50"
          >
            <IconSparkles size={16} />
            {refining === viewSlides.id ? "Refining..." : viewSlides.status === "refined" ? "Re-refine" : "Refine with AI"}
          </button>
          {viewSlides.status === "refined" && (
            <button
              onClick={() => handleDevelop(viewSlides)}
              disabled={developing}
              className="flex items-center gap-2 px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)] hover:bg-[var(--color-brand-cyan)]/20 transition-colors disabled:opacity-50"
            >
              <IconPlayerPlay size={16} />
              {developing ? "Starting..." : "Develop Slidedeck"}
            </button>
          )}
          <button
            onClick={() => setEditSlides(viewSlides)}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-white transition-colors"
          >
            <IconPencil size={16} /> Edit
          </button>
          <button
            onClick={() => setDeleteSlides(viewSlides)}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-[var(--radius-md)] bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
          >
            <IconTrash size={16} /> Delete
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">Presentations</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">Create and manage slide presentations</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity min-h-[44px]"
        >
          <IconPlus size={16} />
          {!isMobile && "New Presentation"}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-[var(--color-brand-pink)] border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Empty state */}
      {!loading && slides.length === 0 && (
        <div className="text-center py-12">
          <IconPresentation size={48} className="mx-auto text-[var(--color-text-muted)] mb-4" stroke={1} />
          <p className="text-[var(--color-text-muted)]">No presentations yet</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-4 px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] hover:bg-[var(--color-brand-pink)]/20 transition-colors"
          >
            Create your first presentation
          </button>
        </div>
      )}

      {/* List */}
      {!loading && slides.length > 0 && (
        isMobile ? (
          <div className="space-y-2">
            {slides.map((item) => (
              <button
                key={item.id}
                onClick={() => setViewSlides(item)}
                className="w-full text-left p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] min-h-[44px] active:bg-[var(--color-bg-tertiary)] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <p className="font-medium text-sm flex-1">{item.title}</p>
                  <span className={`px-2 py-0.5 text-[10px] rounded-full flex-shrink-0 ${item.status === "refined" ? "bg-green-500/15 text-green-400" : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"}`}>
                    {item.status === "refined" ? "Refined" : "Draft"}
                  </span>
                </div>
                {item.description && <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{item.description}</p>}
              </button>
            ))}
          </div>
        ) : (
          <div className="border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] text-left">
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Status</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Slides</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Updated</th>
                  <th className="px-4 py-3 font-medium w-32">Actions</th>
                </tr>
              </thead>
              <tbody>
                {slides.map((item) => (
                  <tr key={item.id} className="border-t border-[var(--color-border-dark)] hover:bg-[var(--color-bg-secondary)] transition-colors cursor-pointer" onClick={() => setViewSlides(item)}>
                    <td className="px-4 py-3">
                      <p className="font-medium">{item.title}</p>
                      {item.description && <p className="text-xs text-[var(--color-text-muted)] mt-0.5 line-clamp-1">{item.description}</p>}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className={`px-2 py-0.5 text-[10px] rounded-full ${item.status === "refined" ? "bg-green-500/15 text-green-400" : "bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]"}`}>
                        {item.status === "refined" ? "Refined" : "Draft"}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-[var(--color-text-muted)]">
                      {item.sections.length || "—"}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-[var(--color-text-muted)]">
                      {new Date(item.updatedAt).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => setEditSlides(item)} className="p-1.5 rounded hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] hover:text-white transition-colors">
                          <IconPencil size={14} />
                        </button>
                        <button onClick={() => setDeleteSlides(item)} className="p-1.5 rounded hover:bg-red-500/10 text-[var(--color-text-muted)] hover:text-red-400 transition-colors">
                          <IconTrash size={14} />
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

      {/* Mobile detail bottom sheet */}
      {viewSlides && isMobile && (
        <MobileBottomSheet open={!!viewSlides} onClose={() => setViewSlides(null)} title={viewSlides.title}>
          {slidesDetailContent}
        </MobileBottomSheet>
      )}

      {/* Create dialog */}
      {showCreate && (
        isMobile ? (
          <MobileBottomSheet open={showCreate} onClose={() => setShowCreate(false)} title="New Presentation">
            <SlidesForm
              onSubmit={async (title, description, attachments) => {
                await slidesApi.create({ title, description, attachments });
                toast.success("Presentation created");
                setShowCreate(false);
                loadSlides();
              }}
            />
          </MobileBottomSheet>
        ) : (
          <SlidesDialog
            onClose={() => setShowCreate(false)}
            onSubmit={async (title, description, attachments) => {
              await slidesApi.create({ title, description, attachments });
              toast.success("Presentation created");
              setShowCreate(false);
              loadSlides();
            }}
          />
        )
      )}

      {/* Edit dialog */}
      {editSlides && (
        isMobile ? (
          <MobileBottomSheet open={!!editSlides} onClose={() => setEditSlides(null)} title="Edit Presentation">
            <SlidesForm
              initialTitle={editSlides.title}
              initialDescription={editSlides.description}
              initialAttachments={editSlides.attachments}
              onSubmit={async (title, description, attachments) => {
                const updated = await slidesApi.update(editSlides.id, { title, description, attachments });
                toast.success("Presentation updated");
                setEditSlides(null);
                setSlides((prev) => prev.map((s) => (s.id === editSlides.id ? updated : s)));
                if (viewSlides?.id === editSlides.id) setViewSlides(updated);
              }}
            />
          </MobileBottomSheet>
        ) : (
          <SlidesDialog
            initialTitle={editSlides.title}
            initialDescription={editSlides.description}
            initialAttachments={editSlides.attachments}
            onClose={() => setEditSlides(null)}
            onSubmit={async (title, description, attachments) => {
              const updated = await slidesApi.update(editSlides.id, { title, description, attachments });
              toast.success("Presentation updated");
              setEditSlides(null);
              setSlides((prev) => prev.map((s) => (s.id === editSlides.id ? updated : s)));
              if (viewSlides?.id === editSlides.id) setViewSlides(updated);
            }}
          />
        )
      )}

      {/* Delete confirmation */}
      {deleteSlides && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-sm space-y-4">
            <h2 className="text-lg font-semibold">Delete Presentation</h2>
            <p className="text-sm text-[var(--color-text-muted)]">
              Are you sure you want to delete &quot;{deleteSlides.title}&quot;? This cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setDeleteSlides(null)} className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-white transition-colors">
                Cancel
              </button>
              <button
                onClick={async () => {
                  await slidesApi.delete(deleteSlides.id);
                  toast.success("Presentation deleted");
                  setSlides((prev) => prev.filter((s) => s.id !== deleteSlides.id));
                  if (viewSlides?.id === deleteSlides.id) setViewSlides(null);
                  setDeleteSlides(null);
                }}
                className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-red-500 text-white hover:bg-red-600 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ── */

function SlidesFilesSection({ slides, onFilesChange }: { slides: SlidesItem; onFilesChange: (item: SlidesItem, attachments: string[]) => Promise<void> }) {
  return (
    <div className="space-y-3">
      {slides.attachments?.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {slides.attachments.map((url, i) => {
            const name = url.split("/").pop() || "template.pptx";
            const shortName = name.length > 24 ? name.slice(0, 21) + "..." : name;
            return (
              <a key={`pptx-${i}`} href={getUploadUrl(url)} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-xs hover:border-[var(--color-brand-pink)]/30 transition-colors">
                <IconPresentation size={14} className="text-blue-400 shrink-0" />
                <span className="text-[var(--color-text-secondary)] truncate max-w-[140px]">{shortName}</span>
              </a>
            );
          })}
        </div>
      )}
      <ImageUpload images={[]} onChange={() => {}}
        attachments={slides.attachments || []} onAttachmentsChange={(attachments) => onFilesChange(slides, attachments)} acceptPdf={false} accept=".pptx" label="PowerPoint Template" />
    </div>
  );
}

function SlidesForm({ initialTitle = "", initialDescription = "", initialAttachments = [] as string[], onSubmit }: {
  initialTitle?: string; initialDescription?: string; initialAttachments?: string[];
  onSubmit: (title: string, description: string, attachments: string[]) => Promise<void>;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [attachments, setAttachments] = useState<string[]>(initialAttachments);
  const [submitting, setSubmitting] = useState(false);

  return (
    <div className="space-y-4 p-4">
      <input type="text" placeholder="Presentation title" value={title} onChange={(e) => setTitle(e.target.value)}
        className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors min-h-[44px]" />
      <textarea placeholder="Describe your presentation — topic, audience, key points..." value={description} onChange={(e) => setDescription(e.target.value)} rows={4}
        className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none" />
      <div>
        <label className="text-xs text-[var(--color-text-muted)] mb-1 block">PowerPoint Template (.pptx)</label>
        <ImageUpload images={[]} onChange={() => {}} attachments={attachments} onAttachmentsChange={setAttachments} acceptPdf={false} accept=".pptx" label="PowerPoint Template" />
      </div>
      <button onClick={async () => { if (!title.trim()) return; setSubmitting(true); try { await onSubmit(title, description, attachments); } catch { toast.error("Failed"); } finally { setSubmitting(false); } }}
        disabled={submitting || !title.trim()}
        className="w-full px-4 py-3 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 min-h-[44px]">
        {submitting ? "Saving..." : "Save"}
      </button>
    </div>
  );
}

function SlidesDialog({ initialTitle = "", initialDescription = "", initialAttachments = [] as string[], onClose, onSubmit }: {
  initialTitle?: string; initialDescription?: string; initialAttachments?: string[];
  onClose: () => void;
  onSubmit: (title: string, description: string, attachments: string[]) => Promise<void>;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [attachments, setAttachments] = useState<string[]>(initialAttachments);
  const [submitting, setSubmitting] = useState(false);
  const isEdit = !!initialTitle;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-lg space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{isEdit ? "Edit Presentation" : "New Presentation"}</h2>
          <button onClick={onClose} className="p-1 text-[var(--color-text-muted)] hover:text-white transition-colors"><IconX size={18} /></button>
        </div>
        <input type="text" placeholder="Presentation title" value={title} onChange={(e) => setTitle(e.target.value)}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors" />
        <textarea placeholder="Describe your presentation — topic, audience, key points..." value={description} onChange={(e) => setDescription(e.target.value)} rows={4}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none" />
        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">PowerPoint Template (.pptx)</label>
          <ImageUpload images={[]} onChange={() => {}} attachments={attachments} onAttachmentsChange={setAttachments} acceptPdf={false} accept=".pptx" label="PowerPoint Template" />
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-white transition-colors">Cancel</button>
          <button onClick={async () => { if (!title.trim()) return; setSubmitting(true); try { await onSubmit(title, description, attachments); } catch { toast.error("Failed"); } finally { setSubmitting(false); } }}
            disabled={submitting || !title.trim()}
            className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity disabled:opacity-50">
            {submitting ? "Saving..." : isEdit ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
