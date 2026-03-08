"use client";

import { useEffect, useState, useCallback } from "react";
import { IconPlus, IconPencil, IconTrash, IconArrowLeft } from "@tabler/icons-react";
import { toast } from "sonner";
import { notesApi, getUploadUrl, type Note } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { ImageUpload } from "@/components/ui/image-upload";

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editNote, setEditNote] = useState<Note | null>(null);
  const [deleteNote, setDeleteNote] = useState<Note | null>(null);
  const [viewNote, setViewNote] = useState<Note | null>(null);
  const { t } = useI18n();

  const loadNotes = useCallback(async () => {
    try {
      setLoading(true);
      const data = await notesApi.list();
      setNotes(data);
    } catch {
      toast.error(t("notes.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  return (
    <div className="space-y-6">
      {/* Detail view */}
      {viewNote ? (
        <>
          <button
            onClick={() => setViewNote(null)}
            className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <IconArrowLeft size={16} /> {t("notes.backToList")}
          </button>
          <div>
            <h1 className="text-2xl font-semibold gradient-brand-text">{viewNote.title}</h1>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              {new Date(viewNote.updatedAt).toLocaleDateString()}
            </p>
          </div>
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)]">
            <p className="text-sm whitespace-pre-wrap">{viewNote.content}</p>
          </div>
          {viewNote.images && viewNote.images.length > 0 && (
            <div className="flex flex-wrap gap-3">
              {viewNote.images.map((url, i) => (
                <img
                  key={i}
                  src={getUploadUrl(url)}
                  alt=""
                  className="w-32 h-32 object-cover rounded-[var(--radius-md)] border border-[var(--color-border-dark)]"
                />
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => { setEditNote(viewNote); setViewNote(null); }}
              className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              <IconPencil size={16} /> {t("notes.edit")}
            </button>
            <button
              onClick={() => { setDeleteNote(viewNote); }}
              className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
            >
              <IconTrash size={16} /> {t("notes.delete")}
            </button>
          </div>
        </>
      ) : (
      <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{t("notes.title")}</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            {t("notes.subtitle")}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <IconPlus size={16} />
          {t("notes.create")}
        </button>
      </div>

      {/* Notes Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-text-muted)]">
          {t("notes.loading")}
        </div>
      ) : notes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-[var(--color-text-muted)]">
          <p>{t("notes.empty")}</p>
          <p className="text-xs mt-1">{t("notes.emptyHint")}</p>
        </div>
      ) : (
        <div className="border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] text-left">
                <th className="px-4 py-3 font-medium">{t("notes.colTitle")}</th>
                <th className="px-4 py-3 font-medium hidden md:table-cell">{t("notes.colContent")}</th>
                <th className="px-4 py-3 font-medium hidden lg:table-cell">{t("notes.colUpdated")}</th>
                <th className="px-4 py-3 font-medium w-24">{t("notes.colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {notes.map((note) => (
                <tr
                  key={note.id}
                  className="border-t border-[var(--color-border-dark)] hover:bg-[var(--color-bg-secondary)] transition-colors cursor-pointer"
                  onClick={() => setViewNote(note)}
                >
                  <td className="px-4 py-3 font-medium">{note.title}</td>
                  <td className="px-4 py-3 text-[var(--color-text-secondary)] hidden md:table-cell truncate max-w-xs">
                    {note.content.slice(0, 80)}
                    {note.content.length > 80 ? "..." : ""}
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-muted)] hidden lg:table-cell">
                    {new Date(note.updatedAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => setEditNote(note)}
                        className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-brand-cyan)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
                        title={t("notes.edit")}
                      >
                        <IconPencil size={16} />
                      </button>
                      <button
                        onClick={() => setDeleteNote(note)}
                        className="p-1.5 rounded text-[var(--color-text-muted)] hover:text-red-400 hover:bg-[var(--color-bg-tertiary)] transition-colors"
                        title={t("notes.delete")}
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
      )}
      </>
      )}

      {/* Create Dialog */}
      {showCreate && (
        <NoteDialog
          onClose={() => setShowCreate(false)}
          onSubmit={async (title, content, images) => {
            await notesApi.create({ title, content, images });
            toast.success(t("notes.created"));
            setShowCreate(false);
            loadNotes();
          }}
        />
      )}

      {/* Edit Dialog */}
      {editNote && (
        <NoteDialog
          initialTitle={editNote.title}
          initialContent={editNote.content}
          initialImages={editNote.images ?? []}
          onClose={() => setEditNote(null)}
          onSubmit={async (title, content, images) => {
            await notesApi.update(editNote.id, { title, content, images });
            toast.success(t("notes.updated"));
            setEditNote(null);
            loadNotes();
          }}
        />
      )}

      {/* Delete Dialog */}
      {deleteNote && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-sm space-y-4">
            <h2 className="text-lg font-semibold">{t("notes.deleteDialog")}</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {t("notes.deleteConfirm")} &ldquo;{deleteNote.title}&rdquo;? {t("notes.deleteWarning")}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteNote(null)}
                className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
              >
                {t("notes.cancel")}
              </button>
              <button
                onClick={async () => {
                  await notesApi.delete(deleteNote.id);
                  toast.success(t("notes.deleted"));
                  setDeleteNote(null);
                  loadNotes();
                }}
                className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                {t("notes.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function NoteDialog({
  initialTitle = "",
  initialContent = "",
  initialImages = [],
  onClose,
  onSubmit,
}: {
  initialTitle?: string;
  initialContent?: string;
  initialImages?: string[];
  onClose: () => void;
  onSubmit: (title: string, content: string, images: string[]) => Promise<void>;
}) {
  const [noteTitle, setNoteTitle] = useState(initialTitle);
  const [noteContent, setNoteContent] = useState(initialContent);
  const [images, setImages] = useState<string[]>(initialImages);
  const [submitting, setSubmitting] = useState(false);
  const { t } = useI18n();
  const isEdit = !!initialTitle;

  const handleSubmit = async () => {
    if (!noteTitle.trim() || !noteContent.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(noteTitle, noteContent, images);
    } catch {
      toast.error(t("notes.failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-lg space-y-4">
        <h2 className="text-lg font-semibold">{isEdit ? t("notes.editDialog") : t("notes.createDialog")}</h2>
        <div className="space-y-3">
          <input
            type="text"
            placeholder={t("notes.titlePlaceholder")}
            value={noteTitle}
            onChange={(e) => setNoteTitle(e.target.value)}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors"
          />
          <textarea
            placeholder={t("notes.contentPlaceholder")}
            value={noteContent}
            onChange={(e) => setNoteContent(e.target.value)}
            rows={6}
            className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none"
          />
          <ImageUpload images={images} onChange={setImages} />
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
          >
            {t("notes.cancel")}
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !noteTitle.trim() || !noteContent.trim()}
            className="px-4 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {submitting ? t("notes.saving") : t("notes.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
