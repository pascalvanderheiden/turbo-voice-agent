"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { IconPlus, IconTrash, IconArrowLeft, IconSearch, IconWorldWww, IconBrain, IconExternalLink, IconLoader2 } from "@tabler/icons-react";
import { toast } from "sonner";
import { researchApi, ideasApi, type Research, type Idea } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { MobileBottomSheet } from "@/components/ui/mobile-bottom-sheet";

export default function ResearchPage() {
  const [entries, setEntries] = useState<Research[]>([]);
  const [loading, setLoading] = useState(true);
  const [showSearch, setShowSearch] = useState(false);
  const [deleteEntry, setDeleteEntry] = useState<Research | null>(null);
  const [viewEntry, setViewEntry] = useState<Research | null>(null);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [searching, setSearching] = useState(false);
  const { t } = useI18n();
  const isMobile = useIsMobile();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadEntries = useCallback(async () => {
    try {
      setLoading(true);
      const data = await researchApi.list();
      setEntries(data);
    } catch {
      toast.error(t("research.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  // Poll for pending entries
  const hasPending = entries.some((e) => e.status === "pending");
  useEffect(() => {
    if (!hasPending) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const data = await researchApi.list();
        setEntries((prev) => {
          // Notify on status changes
          for (const entry of data) {
            const old = prev.find((p) => p.id === entry.id);
            if (old && old.status === "pending" && entry.status === "completed") {
              toast.success(`${t("research.statusCompleted")}: ${entry.title}`);
            } else if (old && old.status === "pending" && entry.status === "failed") {
              toast.error(`${t("research.statusFailed")}: ${entry.title}`);
            }
          }
          return data;
        });
        // Update detail view if viewing a pending entry
        setViewEntry((v) => {
          if (!v || v.status !== "pending") return v;
          const updated = data.find((e) => e.id === v.id);
          return updated ?? v;
        });
      } catch { /* ignore polling errors */ }
    }, 3000);
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [hasPending, t]);

  // Detail view (desktop only — mobile uses bottom sheet)
  if (!isMobile && viewEntry) {
    const isPending = viewEntry.status === "pending";
    return (
      <div className="space-y-6">
        <button onClick={() => setViewEntry(null)} className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
          <IconArrowLeft size={16} /> {t("research.backToList")}
        </button>

        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">{viewEntry.title}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                  viewEntry.mode === "deep_research"
                    ? "bg-[var(--color-brand-purple)]/10 text-[var(--color-brand-purple)]"
                    : "bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)]"
                }`}>
                  {viewEntry.mode === "deep_research" ? <IconBrain size={12} /> : <IconWorldWww size={12} />}
                  {viewEntry.mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch")}
                </span>
                <StatusBadge status={viewEntry.status} t={t} />
              </div>
            </div>
          </div>

          {isPending && (
            <div className="flex items-center gap-3 p-4 rounded-[var(--radius-md)] bg-yellow-500/5 border border-yellow-500/20">
              <IconLoader2 size={20} className="animate-spin text-yellow-500" />
              <div>
                <p className="text-sm font-medium text-yellow-500">{t("research.statusPending")}</p>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {viewEntry.mode === "deep_research" ? t("research.researching") : t("research.searching")}
                </p>
              </div>
            </div>
          )}

          {viewEntry.result && (
            <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-[var(--color-text-secondary)]">
              {viewEntry.result}
            </div>
          )}

          {viewEntry.error && (
            <div className="text-sm text-red-500 bg-red-500/10 rounded-[var(--radius-md)] p-3">
              {viewEntry.error}
            </div>
          )}

          {viewEntry.citations.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">{t("research.citations")} ({viewEntry.citations.length})</h3>
              <div className="space-y-1">
                {viewEntry.citations.map((c, i) => (
                  <a
                    key={i}
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-[var(--color-brand-cyan)] hover:underline"
                  >
                    <IconExternalLink size={14} />
                    {c.title || c.url}
                  </a>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-2 border-t border-[var(--color-border-dark)]">
            <button
              onClick={() => { setDeleteEntry(viewEntry); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-red-500/10 text-red-500 hover:bg-red-500/20"
            >
              <IconTrash size={14} /> {t("research.delete")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Mobile detail bottom sheet */}
      {isMobile && viewEntry && (
        <MobileBottomSheet open={!!viewEntry} onClose={() => setViewEntry(null)} title={viewEntry.title}>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                viewEntry.mode === "deep_research"
                  ? "bg-[var(--color-brand-purple)]/10 text-[var(--color-brand-purple)]"
                  : "bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)]"
              }`}>
                {viewEntry.mode === "deep_research" ? <IconBrain size={12} /> : <IconWorldWww size={12} />}
                {viewEntry.mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch")}
              </span>
              <StatusBadge status={viewEntry.status} t={t} />
            </div>
            {viewEntry.status === "pending" && (
              <div className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] bg-yellow-500/5 border border-yellow-500/20">
                <IconLoader2 size={16} className="animate-spin text-yellow-500" />
                <p className="text-sm text-yellow-500">{viewEntry.mode === "deep_research" ? t("research.researching") : t("research.searching")}</p>
              </div>
            )}
            {viewEntry.result && <div className="text-sm whitespace-pre-wrap text-[var(--color-text-secondary)]">{viewEntry.result}</div>}
            {viewEntry.error && <div className="text-sm text-red-500 bg-red-500/10 rounded-[var(--radius-md)] p-3">{viewEntry.error}</div>}
            {viewEntry.citations.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium">{t("research.citations")} ({viewEntry.citations.length})</h3>
                {viewEntry.citations.map((c, i) => (
                  <a key={i} href={c.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-[var(--color-brand-cyan)] hover:underline">
                    <IconExternalLink size={14} /> {c.title || c.url}
                  </a>
                ))}
              </div>
            )}
            <button onClick={() => { setDeleteEntry(viewEntry); }} className="flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] text-sm bg-red-600 text-white hover:bg-red-700 transition-colors min-h-[44px]">
              <IconTrash size={14} /> {t("research.delete")}
            </button>
          </div>
        </MobileBottomSheet>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{t("research.title")}</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">{t("research.subtitle")}</p>
        </div>
        {!isMobile && (
        <button
          onClick={async () => {
            setShowSearch(true);
            try { setIdeas(await ideasApi.list()); } catch { /* ignore */ }
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <IconPlus size={16} /> {t("research.newSearch")}
        </button>
        )}
      </div>

      {loading ? (
        <p className="text-[var(--color-text-muted)] text-sm">{t("research.loading")}</p>
      ) : entries.length === 0 ? (
        <div className="text-center py-16 text-[var(--color-text-muted)]">
          <IconSearch size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">{t("research.empty")}</p>
          <p className="text-sm mt-1">{t("research.emptyHint")}</p>
        </div>
      ) : (
        isMobile ? (
          <div className="space-y-2">
            {entries.map((entry) => (
              <button
                key={entry.id}
                onClick={() => setViewEntry(entry)}
                className="w-full text-left p-4 rounded-[var(--radius-lg)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] min-h-[44px] active:bg-[var(--color-bg-tertiary)] transition-colors"
              >
                <div className="flex items-center gap-2">
                  {entry.status === "pending" && <IconLoader2 size={14} className="animate-spin text-yellow-500 flex-shrink-0" />}
                  <p className="font-medium text-sm flex-1 line-clamp-1">{entry.title}</p>
                  <StatusBadge status={entry.status} t={t} />
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="inline-flex items-center gap-1 text-[10px] text-[var(--color-text-muted)]">
                    {entry.mode === "deep_research" ? <IconBrain size={10} /> : <IconWorldWww size={10} />}
                    {entry.mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch")}
                  </span>
                  <span className="text-[10px] text-[var(--color-text-muted)]">{new Date(entry.updatedAt).toLocaleDateString()}</span>
                </div>
              </button>
            ))}
          </div>
        ) : (
        <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border-dark)] text-[var(--color-text-muted)]">
                <th className="text-left px-4 py-3 font-medium">{t("research.colTitle")}</th>
                <th className="text-left px-4 py-3 font-medium">{t("research.colMode")}</th>
                <th className="text-left px-4 py-3 font-medium">{t("research.colStatus")}</th>
                <th className="text-left px-4 py-3 font-medium">{t("research.colUpdated")}</th>
                <th className="text-right px-4 py-3 font-medium">{t("research.colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-[var(--color-border-dark)] last:border-0 hover:bg-[var(--color-bg-tertiary)] cursor-pointer"
                  onClick={() => setViewEntry(entry)}
                >
                  <td className="px-4 py-3 font-medium">
                    <div className="flex items-center gap-2">
                      {entry.status === "pending" && <IconLoader2 size={14} className="animate-spin text-yellow-500 flex-shrink-0" />}
                      {entry.title}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-xs">
                      {entry.mode === "deep_research" ? <IconBrain size={12} /> : <IconWorldWww size={12} />}
                      {entry.mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch")}
                    </span>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={entry.status} t={t} /></td>
                  <td className="px-4 py-3 text-[var(--color-text-muted)]">
                    {new Date(entry.updatedAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteEntry(entry); }}
                      className="p-1.5 rounded hover:bg-red-500/10 text-[var(--color-text-muted)] hover:text-red-500"
                      title={t("research.delete")}
                    >
                      <IconTrash size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )
      )}

      {/* New Search Dialog */}
      {showSearch && (
        isMobile ? (
          <MobileBottomSheet open={showSearch} onClose={() => setShowSearch(false)} title={t("research.newSearch")}>
            <MobileSearchForm
              ideas={ideas}
              t={t}
              searching={searching}
              onSearch={async (query, mode, ideaId) => {
                setSearching(true);
                try {
                  const fn = mode === "deep_research" ? researchApi.deepResearch : researchApi.webSearch;
                  const result = await fn(query, ideaId);
                  toast.success(t("research.started"));
                  setShowSearch(false);
                  setEntries((prev) => [result, ...prev]);
                  setViewEntry(result);
                } catch { toast.error(t("research.failed")); }
                finally { setSearching(false); }
              }}
            />
          </MobileBottomSheet>
        ) : (
        <SearchDialog
          ideas={ideas}
          t={t}
          searching={searching}
          onSearch={async (query, mode, ideaId) => {
            setSearching(true);
            try {
              const fn = mode === "deep_research" ? researchApi.deepResearch : researchApi.webSearch;
              const result = await fn(query, ideaId);
              toast.success(t("research.started"));
              setShowSearch(false);
              setEntries((prev) => [result, ...prev]);
              setViewEntry(result);
            } catch {
              toast.error(t("research.failed"));
            } finally {
              setSearching(false);
            }
          }}
          onClose={() => setShowSearch(false)}
        />
        )
      )}

      {/* Delete Dialog */}
      {deleteEntry && (
        <DialogOverlay onClose={() => setDeleteEntry(null)}>
          <h2 className="text-lg font-semibold mb-2">{t("research.deleteDialog")}</h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-1">{t("research.deleteConfirm")}</p>
          <p className="text-xs text-[var(--color-text-muted)] mb-4">{t("research.deleteWarning")}</p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setDeleteEntry(null)} className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-tertiary)]">
              {t("notes.cancel")}
            </button>
            <button
              onClick={async () => {
                const entry = deleteEntry;
                if (!entry) return;
                try {
                  await researchApi.delete(entry.id);
                  toast.success(t("research.deleted"));
                  setEntries((prev) => prev.filter((e) => e.id !== entry.id));
                  if ((viewEntry as Research | null)?.id === entry.id) setViewEntry(null);
                } catch { toast.error(t("research.failed")); }
                setDeleteEntry(null);
              }}
              className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-red-500 text-white hover:bg-red-600"
            >
              {t("research.delete")}
            </button>
          </div>
        </DialogOverlay>
      )}

      {/* Mobile FAB */}
      {isMobile && !showSearch && !viewEntry && (
        <button
          onClick={async () => {
            setShowSearch(true);
            try { setIdeas(await ideasApi.list()); } catch { /* ignore */ }
          }}
          className="fixed bottom-20 right-4 z-30 flex items-center justify-center w-14 h-14 rounded-full bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white shadow-lg hover:opacity-90 transition-opacity"
          title={t("research.newSearch")}
        >
          <IconPlus size={24} />
        </button>
      )}
    </div>
  );
}

function MobileSearchForm({
  ideas,
  t,
  searching,
  onSearch,
}: {
  ideas: Idea[];
  t: (k: string) => string;
  searching: boolean;
  onSearch: (query: string, mode: "web_search" | "deep_research", ideaId?: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"web_search" | "deep_research">("web_search");
  const [ideaId, setIdeaId] = useState<string>("");

  return (
    <div className="space-y-4">
      <textarea value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("research.queryPlaceholder")} rows={3}
        className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-sm resize-none focus:outline-none focus:border-[var(--color-brand-pink)]" />
      <div className="flex gap-2">
        <button onClick={() => setMode("web_search")}
          className={`flex-1 flex items-center justify-center gap-2 px-3 py-3 rounded-[var(--radius-md)] text-sm border transition-colors min-h-[44px] ${
            mode === "web_search" ? "border-[var(--color-brand-cyan)] bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)]" : "border-[var(--color-border-dark)] text-[var(--color-text-secondary)]"
          }`}>
          <IconWorldWww size={16} /> {t("research.webSearch")}
        </button>
        <button disabled title="Deep research is temporarily unavailable"
          className="flex-1 flex items-center justify-center gap-2 px-3 py-3 rounded-[var(--radius-md)] text-sm border border-[var(--color-border-dark)] text-[var(--color-text-muted)] opacity-50 cursor-not-allowed min-h-[44px]">
          <IconBrain size={16} /> {t("research.deepResearch")}
        </button>
      </div>
      {ideas.length > 0 && (
        <div>
          <label className="text-xs text-[var(--color-text-muted)] mb-1 block">{t("research.linkIdea")}</label>
          <select value={ideaId} onChange={(e) => setIdeaId(e.target.value)} title={t("research.linkIdea")}
            className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-sm focus:outline-none min-h-[44px]">
            <option value="">{t("research.noIdea")}</option>
            {ideas.map((idea) => <option key={idea.id} value={idea.id}>{idea.title}</option>)}
          </select>
        </div>
      )}
      <button disabled={!query.trim() || searching} onClick={() => onSearch(query, mode, ideaId || undefined)}
        className="w-full px-4 py-3 rounded-[var(--radius-md)] text-sm bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white font-medium hover:opacity-90 disabled:opacity-50 min-h-[44px]">
        {searching ? (mode === "deep_research" ? t("research.researching") : t("research.searching")) : (mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch"))}
      </button>
    </div>
  );
}

function StatusBadge({ status, t }: { status: string; t: (k: string) => string }) {
  const map: Record<string, { cls: string; key: string }> = {
    pending: { cls: "bg-yellow-500/10 text-yellow-500", key: "research.statusPending" },
    completed: { cls: "bg-green-500/10 text-green-500", key: "research.statusCompleted" },
    failed: { cls: "bg-red-500/10 text-red-500", key: "research.statusFailed" },
  };
  const { cls, key } = map[status] || map.pending;
  return <span className={`text-xs px-2 py-0.5 rounded-full ${cls}`}>{t(key)}</span>;
}

function SearchDialog({
  ideas,
  t,
  searching,
  onSearch,
  onClose,
}: {
  ideas: Idea[];
  t: (k: string) => string;
  searching: boolean;
  onSearch: (query: string, mode: "web_search" | "deep_research", ideaId?: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"web_search" | "deep_research">("web_search");
  const [ideaId, setIdeaId] = useState<string>("");

  return (
    <DialogOverlay onClose={onClose}>
      <h2 className="text-lg font-semibold mb-4">{t("research.newSearch")}</h2>
      <div className="space-y-4">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("research.queryPlaceholder")}
          rows={3}
          className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-sm resize-none focus:outline-none focus:border-[var(--color-brand-pink)]"
        />

        {/* Mode toggle */}
        <div className="flex gap-2">
          <button
            onClick={() => setMode("web_search")}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-[var(--radius-md)] text-sm border transition-colors ${
              mode === "web_search"
                ? "border-[var(--color-brand-cyan)] bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)]"
                : "border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]"
            }`}
          >
            <IconWorldWww size={16} /> {t("research.webSearch")}
          </button>
          <button
            disabled
            title="Deep research is temporarily unavailable (quota limit)"
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-[var(--radius-md)] text-sm border transition-colors border-[var(--color-border-dark)] text-[var(--color-text-muted)] opacity-50 cursor-not-allowed"
          >
            <IconBrain size={16} /> {t("research.deepResearch")}
            <span className="text-[10px] opacity-70">(unavailable)</span>
          </button>
        </div>

        {/* Link to idea */}
        {ideas.length > 0 && (
          <div>
            <label className="text-xs text-[var(--color-text-muted)] mb-1 block">{t("research.linkIdea")}</label>
            <select
              value={ideaId}
              onChange={(e) => setIdeaId(e.target.value)}
              title={t("research.linkIdea")}
              className="w-full px-3 py-2 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-sm focus:outline-none"
            >
              <option value="">{t("research.noIdea")}</option>
              {ideas.map((idea) => (
                <option key={idea.id} value={idea.id}>{idea.title}</option>
              ))}
            </select>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-tertiary)]">
            {t("notes.cancel")}
          </button>
          <button
            disabled={!query.trim() || searching}
            onClick={() => onSearch(query, mode, ideaId || undefined)}
            className="px-4 py-1.5 rounded-[var(--radius-md)] text-sm bg-gradient-to-r from-[var(--color-brand-pink)] to-[var(--color-brand-purple)] text-white font-medium hover:opacity-90 disabled:opacity-50"
          >
            {searching
              ? mode === "deep_research" ? t("research.researching") : t("research.searching")
              : mode === "deep_research" ? t("research.deepResearch") : t("research.webSearch")
            }
          </button>
        </div>
      </div>
    </DialogOverlay>
  );
}

function DialogOverlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-lg shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
