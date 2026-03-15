"use client";

import { useCallback, useEffect, useState } from "react";
import {
  IconPlus,
  IconPencil,
  IconTrash,
  IconArrowLeft,
  IconCheck,
  IconCircle,
  IconCircleCheck,
  IconCalendar,
  IconPlugConnectedX,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { useI18n } from "@/lib/i18n";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { MobileBottomSheet } from "@/components/ui/mobile-bottom-sheet";
import { todosApi, connectionsApi, type Todo, type TodoCreate, type TodoUpdate } from "@/lib/api";

export default function TodosPage() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editTodo, setEditTodo] = useState<Todo | null>(null);
  const [deleteTodo, setDeleteTodo] = useState<Todo | null>(null);
  const [viewTodo, setViewTodo] = useState<Todo | null>(null);
  const { t } = useI18n();
  const isMobile = useIsMobile();

  // Check connection status first
  useEffect(() => {
    connectionsApi.microsoftTodo
      .status()
      .then((s) => setConnected(s.connected))
      .catch(() => setConnected(false));
  }, []);

  const loadTodos = useCallback(async () => {
    if (connected === false) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const data = await todosApi.list();
      setTodos(data);
    } catch {
      toast.error(t("todos.loadFailed") || "Failed to load to-dos");
    } finally {
      setLoading(false);
    }
  }, [connected, t]);

  useEffect(() => {
    if (connected === true) loadTodos();
    else if (connected === false) setLoading(false);
  }, [connected, loadTodos]);

  // ── Toggle completion ──
  const handleToggleComplete = async (todo: Todo) => {
    try {
      const updated = await todosApi.update(todo.id, { isCompleted: !todo.isCompleted });
      setTodos((prev) => prev.map((t) => (t.id === todo.id ? { ...t, ...updated } : t)));
    } catch {
      toast.error(t("todos.failed") || "Operation failed");
    }
  };

  // ── Not connected prompt ──
  if (connected === false) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
        <IconPlugConnectedX size={48} stroke={1.5} className="text-[var(--color-text-muted)]" />
        <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
          {t("todos.notConnectedTitle") || "Connect Microsoft To-Do"}
        </h2>
        <p className="text-sm text-[var(--color-text-muted)] max-w-md">
          {t("todos.notConnectedHint") || "Connect your Microsoft account in the user menu to manage your to-dos."}
        </p>
      </div>
    );
  }

  // ── Loading ──
  if (loading || connected === null) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-[var(--color-text-muted)]">{t("todos.loading") || "Loading to-dos..."}</p>
      </div>
    );
  }

  // ── Desktop detail view ──
  if (!isMobile && viewTodo) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setViewTodo(null)}
          className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <IconArrowLeft size={16} /> {t("todos.backToList") || "Back to to-dos"}
        </button>
        <div>
          <div className="flex items-center gap-3">
            <button onClick={() => handleToggleComplete(viewTodo)}>
              {viewTodo.isCompleted ? (
                <IconCircleCheck size={24} className="text-emerald-400" />
              ) : (
                <IconCircle size={24} className="text-[var(--color-text-muted)]" />
              )}
            </button>
            <h1 className={`text-2xl font-semibold ${viewTodo.isCompleted ? "line-through text-[var(--color-text-muted)]" : "gradient-brand-text"}`}>
              {viewTodo.title}
            </h1>
          </div>
          {viewTodo.dueDate && (
            <p className="text-xs text-[var(--color-text-muted)] mt-1 flex items-center gap-1">
              <IconCalendar size={12} /> {new Date(viewTodo.dueDate).toLocaleDateString()}
            </p>
          )}
        </div>
        {viewTodo.notes && (
          <div className="p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)]">
            <p className="text-sm whitespace-pre-wrap">{viewTodo.notes}</p>
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={() => { setEditTodo(viewTodo); setViewTodo(null); }}
            className="flex items-center gap-1 px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
          >
            <IconPencil size={16} /> {t("todos.edit") || "Edit"}
          </button>
          <button
            onClick={() => setDeleteTodo(viewTodo)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-[var(--radius-md)] text-sm text-red-400 bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
          >
            <IconTrash size={16} /> {t("todos.delete") || "Delete"}
          </button>
        </div>
      </div>
    );
  }

  // ── Mobile detail bottom sheet ──
  if (isMobile && viewTodo) {
    return (
      <>
        <MobileBottomSheet open={!!viewTodo} onClose={() => setViewTodo(null)} title={viewTodo.title}>
          <div className="space-y-4 px-4 pb-6">
            <div className="flex items-center gap-2">
              <button onClick={() => handleToggleComplete(viewTodo)}>
                {viewTodo.isCompleted ? (
                  <IconCircleCheck size={20} className="text-emerald-400" />
                ) : (
                  <IconCircle size={20} className="text-[var(--color-text-muted)]" />
                )}
              </button>
              <span className={viewTodo.isCompleted ? "line-through text-[var(--color-text-muted)]" : ""}>
                {viewTodo.title}
              </span>
            </div>
            {viewTodo.dueDate && (
              <p className="text-xs text-[var(--color-text-muted)] flex items-center gap-1">
                <IconCalendar size={12} /> {new Date(viewTodo.dueDate).toLocaleDateString()}
              </p>
            )}
            {viewTodo.notes && <p className="text-sm whitespace-pre-wrap">{viewTodo.notes}</p>}
            <div className="flex gap-2">
              <button
                onClick={() => { setEditTodo(viewTodo); setViewTodo(null); }}
                className="flex-1 py-2 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-secondary)] text-center"
              >
                {t("todos.edit") || "Edit"}
              </button>
              <button
                onClick={() => { setDeleteTodo(viewTodo); setViewTodo(null); }}
                className="flex-1 py-2 rounded-[var(--radius-md)] text-sm bg-red-500/10 text-red-400 text-center"
              >
                {t("todos.delete") || "Delete"}
              </button>
            </div>
          </div>
        </MobileBottomSheet>
        <TodoList
          todos={todos}
          t={t}
          isMobile={isMobile}
          onView={setViewTodo}
          onToggle={handleToggleComplete}
          onShowCreate={() => setShowCreate(true)}
        />
      </>
    );
  }

  // ── List view ──
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{t("todos.title") || "To-Dos"}</h1>
          <p className="text-sm text-[var(--color-text-muted)]">{t("todos.subtitle") || "Manage your Microsoft To-Do tasks"}</p>
        </div>
        {!isMobile && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-1 px-3 py-2 rounded-[var(--radius-md)] text-sm bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity"
          >
            <IconPlus size={16} /> {t("todos.create") || "New To-Do"}
          </button>
        )}
      </div>

      {todos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <IconCheck size={40} stroke={1.5} className="text-[var(--color-text-muted)]" />
          <p className="text-sm text-[var(--color-text-muted)]">{t("todos.empty") || "No to-dos yet"}</p>
          <p className="text-xs text-[var(--color-text-muted)]">{t("todos.emptyHint") || "Create your first to-do or use voice mode"}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {todos.map((todo) => (
            <div
              key={todo.id}
              className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] cursor-pointer hover:bg-[var(--color-bg-tertiary)] transition-colors"
            >
              <button
                onClick={(e) => { e.stopPropagation(); handleToggleComplete(todo); }}
                className="flex-shrink-0"
              >
                {todo.isCompleted ? (
                  <IconCircleCheck size={20} className="text-emerald-400" />
                ) : (
                  <IconCircle size={20} className="text-[var(--color-text-muted)] hover:text-[var(--color-brand-pink)]" />
                )}
              </button>
              <div className="flex-1 min-w-0" onClick={() => setViewTodo(todo)}>
                <p className={`text-sm font-medium truncate ${todo.isCompleted ? "line-through text-[var(--color-text-muted)]" : "text-[var(--color-text-primary)]"}`}>
                  {todo.title}
                </p>
                {todo.dueDate && (
                  <p className="text-xs text-[var(--color-text-muted)] flex items-center gap-1 mt-0.5">
                    <IconCalendar size={11} /> {new Date(todo.dueDate).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Mobile FAB */}
      {isMobile && (
        <button
          onClick={() => setShowCreate(true)}
          className="fixed bottom-20 right-4 w-14 h-14 rounded-full bg-[var(--color-brand-pink)] text-white flex items-center justify-center shadow-lg z-30"
        >
          <IconPlus size={24} />
        </button>
      )}

      {/* Create dialog/sheet */}
      {showCreate && (
        isMobile ? (
          <MobileBottomSheet open={showCreate} onClose={() => setShowCreate(false)} title={t("todos.createDialog") || "Create To-Do"}>
            <TodoForm
              onSubmit={async (data) => {
                await todosApi.create(data as TodoCreate);
                toast.success(t("todos.created") || "To-do created");
                setShowCreate(false);
                loadTodos();
              }}
              onCancel={() => setShowCreate(false)}
              t={t}
            />
          </MobileBottomSheet>
        ) : (
          <DialogOverlay onClose={() => setShowCreate(false)} title={t("todos.createDialog") || "Create To-Do"}>
            <TodoForm
              onSubmit={async (data) => {
                await todosApi.create(data as TodoCreate);
                toast.success(t("todos.created") || "To-do created");
                setShowCreate(false);
                loadTodos();
              }}
              onCancel={() => setShowCreate(false)}
              t={t}
            />
          </DialogOverlay>
        )
      )}

      {/* Edit dialog/sheet */}
      {editTodo && (
        isMobile ? (
          <MobileBottomSheet open={!!editTodo} onClose={() => setEditTodo(null)} title={t("todos.editDialog") || "Edit To-Do"}>
            <TodoForm
              initial={editTodo}
              onSubmit={async (data) => {
                await todosApi.update(editTodo.id, data);
                toast.success(t("todos.updated") || "To-do updated");
                setEditTodo(null);
                loadTodos();
              }}
              onCancel={() => setEditTodo(null)}
              t={t}
            />
          </MobileBottomSheet>
        ) : (
          <DialogOverlay onClose={() => setEditTodo(null)} title={t("todos.editDialog") || "Edit To-Do"}>
            <TodoForm
              initial={editTodo}
              onSubmit={async (data) => {
                await todosApi.update(editTodo.id, data);
                toast.success(t("todos.updated") || "To-do updated");
                setEditTodo(null);
                loadTodos();
              }}
              onCancel={() => setEditTodo(null)}
              t={t}
            />
          </DialogOverlay>
        )
      )}

      {/* Delete confirmation */}
      {deleteTodo && (
        <DialogOverlay onClose={() => setDeleteTodo(null)} title={t("todos.deleteDialog") || "Delete To-Do"}>
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">
              {t("todos.deleteConfirm") || "Are you sure you want to delete"} &quot;{deleteTodo.title}&quot;?
            </p>
            <p className="text-xs text-[var(--color-text-muted)]">{t("todos.deleteWarning") || "This cannot be undone."}</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeleteTodo(null)}
                className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-secondary)]"
              >
                {t("todos.cancel") || "Cancel"}
              </button>
              <button
                onClick={async () => {
                  try {
                    await todosApi.delete(deleteTodo.id);
                    toast.success(t("todos.deleted") || "To-do deleted");
                    setTodos((prev) => prev.filter((t) => t.id !== deleteTodo.id));
                    if (viewTodo?.id === deleteTodo.id) setViewTodo(null);
                  } catch {
                    toast.error(t("todos.failed") || "Operation failed");
                  }
                  setDeleteTodo(null);
                }}
                className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-red-500 text-white"
              >
                {t("todos.delete") || "Delete"}
              </button>
            </div>
          </div>
        </DialogOverlay>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────

function TodoList({
  todos,
  t,
  isMobile,
  onView,
  onToggle,
  onShowCreate,
}: {
  todos: Todo[];
  t: (k: string) => string;
  isMobile: boolean;
  onView: (t: Todo) => void;
  onToggle: (t: Todo) => void;
  onShowCreate: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold gradient-brand-text">{t("todos.title") || "To-Dos"}</h1>
      </div>
      <div className="space-y-2">
        {todos.map((todo) => (
          <div
            key={todo.id}
            onClick={() => onView(todo)}
            className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] cursor-pointer"
          >
            <button onClick={(e) => { e.stopPropagation(); onToggle(todo); }}>
              {todo.isCompleted ? (
                <IconCircleCheck size={20} className="text-emerald-400" />
              ) : (
                <IconCircle size={20} className="text-[var(--color-text-muted)]" />
              )}
            </button>
            <span className={`text-sm truncate ${todo.isCompleted ? "line-through text-[var(--color-text-muted)]" : ""}`}>
              {todo.title}
            </span>
          </div>
        ))}
      </div>
      {isMobile && (
        <button
          onClick={onShowCreate}
          className="fixed bottom-20 right-4 w-14 h-14 rounded-full bg-[var(--color-brand-pink)] text-white flex items-center justify-center shadow-lg z-30"
        >
          <IconPlus size={24} />
        </button>
      )}
    </div>
  );
}

function TodoForm({
  initial,
  onSubmit,
  onCancel,
  t,
}: {
  initial?: Todo;
  onSubmit: (data: TodoCreate | TodoUpdate) => Promise<void>;
  onCancel: () => void;
  t: (k: string) => string;
}) {
  const [title, setTitle] = useState(initial?.title || "");
  const [notes, setNotes] = useState(initial?.notes || "");
  const [dueDate, setDueDate] = useState(initial?.dueDate ? initial.dueDate.split("T")[0] : "");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      const data: TodoCreate | TodoUpdate = { title: title.trim() };
      if (notes.trim()) data.notes = notes.trim();
      if (dueDate) data.dueDate = dueDate;
      await onSubmit(data);
    } catch {
      toast.error(t("todos.failed") || "Operation failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4">
      <div>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t("todos.titlePlaceholder") || "Task title"}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-sm outline-none focus:ring-1 focus:ring-[var(--color-brand-pink)]"
          autoFocus
          required
        />
      </div>
      <div>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder={t("todos.notesPlaceholder") || "Notes (optional)"}
          rows={3}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-sm outline-none focus:ring-1 focus:ring-[var(--color-brand-pink)] resize-none"
        />
      </div>
      <div>
        <label className="text-xs text-[var(--color-text-muted)] mb-1 block">
          {t("todos.dueDate") || "Due date"}
        </label>
        <input
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-sm outline-none focus:ring-1 focus:ring-[var(--color-brand-pink)]"
        />
      </div>
      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-secondary)]"
        >
          {t("todos.cancel") || "Cancel"}
        </button>
        <button
          type="submit"
          disabled={!title.trim() || saving}
          className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-brand-pink)] text-white disabled:opacity-50"
        >
          {saving ? (t("todos.saving") || "Saving...") : (t("todos.save") || "Save")}
        </button>
      </div>
    </form>
  );
}

function DialogOverlay({
  onClose,
  title,
  children,
}: {
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md mx-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] shadow-xl">
        <div className="px-4 py-3 border-b border-[var(--color-border-dark)]">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{title}</h2>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
