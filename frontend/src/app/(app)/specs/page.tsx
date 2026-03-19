"use client";

import { useCallback, useEffect, useState } from "react";
import {
  IconPlus,
  IconFileCode,
  IconSparkles,
  IconChevronRight,
  IconCode,
  IconUpload,
  IconLoader2,
  IconX,
  IconFileText,
  IconFolderOpen,
} from "@tabler/icons-react";
import { useI18n } from "@/lib/i18n";
import { specsApi, type Spec, type SpecCreate } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";
import { useIsMobile } from "@/hooks/use-is-mobile";
import { MobileBottomSheet } from "@/components/ui/mobile-bottom-sheet";

export default function SpecsPage() {
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importFiles, setImportFiles] = useState<File[]>([]);
  const [importing, setImporting] = useState(false);
  const { t } = useI18n();
  const isMobile = useIsMobile();

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
        {!isMobile && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] text-sm font-medium hover:bg-[var(--color-bg-tertiary)] transition-colors"
          >
            <IconUpload size={16} />
            Import OpenSpec
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          >
            <IconPlus size={16} />
            {t("specs.create")}
          </button>
        </div>
        )}
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
                    <h3 className="font-medium text-sm truncate">{foundation.title.replace(/ — Foundation$/, "")}</h3>
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
                    {foundation.formatVersion === "imported" && (
                      <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-amber-500/15 text-amber-400 flex-shrink-0">
                        Imported
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
        isMobile ? (
          <MobileBottomSheet open={showCreate} onClose={() => setShowCreate(false)} title={t("specs.createDialog")}>
            <SpecForm
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
          </MobileBottomSheet>
        ) : (
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
        )
      )}

      {/* Import OpenSpec Dialog */}
      {showImport && (
        <ImportOpenSpecDialog
          files={importFiles}
          setFiles={setImportFiles}
          importing={importing}
          onClose={() => { setShowImport(false); setImportFiles([]); }}
          onImport={async () => {
            if (importFiles.length === 0) return;
            setImporting(true);
            try {
              const result = await specsApi.importOpenspec(importFiles);
              toast.success(`Imported ${result.featureCount} specs from OpenSpec project`);
              setShowImport(false);
              setImportFiles([]);
              loadData();
              window.location.href = `/specs/${result.foundationId}`;
            } catch (e) {
              toast.error(e instanceof Error ? e.message : "Import failed");
            } finally {
              setImporting(false);
            }
          }}
        />
      )}

      {/* Mobile FAB */}
      {isMobile && !showCreate && (
        <button
          onClick={() => setShowCreate(true)}
          className="fixed bottom-20 right-4 z-30 flex items-center justify-center w-14 h-14 rounded-full bg-[var(--color-brand-pink)] text-white shadow-lg shadow-[var(--color-brand-pink)]/25 hover:opacity-90 transition-opacity"
          title={t("specs.create")}
        >
          <IconPlus size={24} />
        </button>
      )}
    </div>
  );
}

function SpecForm({
  onSubmit,
}: {
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
    <div className="space-y-4">
      <input type="text" placeholder={t("specs.titlePlaceholder")} value={title} onChange={(e) => setTitle(e.target.value)}
        className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors min-h-[44px]" />
      <textarea placeholder={t("specs.contentPlaceholder")} value={content} onChange={(e) => setContent(e.target.value)} rows={6}
        className="w-full px-3 py-3 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-sm focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors resize-none font-mono" />
      <label className="flex items-center gap-2 cursor-pointer min-h-[44px]">
        <input type="checkbox" checked={optimize} onChange={(e) => setOptimize(e.target.checked)} className="accent-[var(--color-brand-purple)]" />
        <IconSparkles size={14} className="text-[var(--color-brand-purple)]" />
        <span className="text-sm text-[var(--color-text-secondary)]">{t("specs.optimize")}</span>
      </label>
      <button onClick={handleSubmit} disabled={submitting || !title.trim()}
        className="w-full px-4 py-3 text-sm rounded-[var(--radius-md)] bg-[var(--color-brand-pink)] text-white hover:opacity-90 transition-opacity disabled:opacity-50 min-h-[44px]">
        {submitting ? t("specs.saving") : t("specs.save")}
      </button>
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

function ImportOpenSpecDialog({
  files,
  setFiles,
  importing,
  onClose,
  onImport,
}: {
  files: File[];
  setFiles: (f: File[]) => void;
  importing: boolean;
  onClose: () => void;
  onImport: () => Promise<void>;
}) {
  const folderName = files.length > 0
    ? ((files[0] as File & { webkitRelativePath?: string }).webkitRelativePath || "").split("/")[0] || "unknown"
    : "";
  const specFiles = files.filter((f) => {
    const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
    return /specs\/[^/]+\/spec\.md$/i.test(rel);
  });
  const changeFiles = files.filter((f) => {
    const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
    return /changes\/[^/]+\/proposal\.md$/i.test(rel);
  });
  const hasProject = files.some((f) => {
    const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
    return /project\.md$/i.test(rel);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-sm flex items-center gap-2">
            <IconFolderOpen size={16} className="text-amber-400" />
            Import OpenSpec Project
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-[var(--color-bg-tertiary)] rounded">
            <IconX size={14} />
          </button>
        </div>

        <p className="text-xs text-[var(--color-text-muted)] mb-4">
          Select a local OpenSpec project folder containing a <code className="px-1 bg-[var(--color-bg-tertiary)] rounded">specs/</code> directory.
          All specs and change history will be imported.
        </p>

        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-[var(--color-text-muted)] mb-1 block">Project Folder</label>
            <input
              type="file"
              /* @ts-expect-error webkitdirectory is non-standard */
              webkitdirectory=""
              directory=""
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
              className="w-full text-xs text-[var(--color-text-muted)] file:mr-3 file:py-1.5 file:px-3 file:rounded-[var(--radius-md)] file:border-0 file:text-xs file:font-medium file:bg-amber-500/10 file:text-amber-400 hover:file:bg-amber-500/20 file:cursor-pointer file:transition-colors"
            />
          </div>

          {files.length > 0 && (
            <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] space-y-2">
              <div className="text-xs font-medium text-[var(--color-text-primary)]">
                📁 {folderName}
              </div>
              <div className="grid grid-cols-2 gap-1 text-[10px] text-[var(--color-text-muted)]">
                <div className="flex items-center gap-1">
                  <IconFileCode size={10} className="text-amber-400" />
                  {specFiles.length} spec{specFiles.length !== 1 ? "s" : ""} found
                </div>
                <div className="flex items-center gap-1">
                  <IconFileText size={10} />
                  {changeFiles.length} change{changeFiles.length !== 1 ? "s" : ""}
                </div>
                <div className="flex items-center gap-1">
                  {hasProject ? "✓" : "✗"} project.md
                </div>
                <div className="flex items-center gap-1">
                  {files.length} total files
                </div>
              </div>
              {specFiles.length > 0 && (
                <div className="mt-1 space-y-0.5">
                  <div className="text-[10px] font-medium text-[var(--color-text-muted)]">Specs:</div>
                  {specFiles.slice(0, 10).map((f, i) => {
                    const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
                    const name = rel.match(/specs\/([^/]+)\//)?.[1] || rel;
                    return (
                      <div key={i} className="text-[10px] text-amber-400/80 flex items-center gap-1">
                        <IconFileCode size={10} /> {name}
                      </div>
                    );
                  })}
                  {specFiles.length > 10 && (
                    <div className="text-[10px] text-[var(--color-text-muted)]">...and {specFiles.length - 10} more</div>
                  )}
                </div>
              )}
              {specFiles.length === 0 && (
                <div className="text-[10px] text-red-400">
                  ⚠ No specs found — the folder must contain specs/&lt;name&gt;/spec.md files
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onImport}
            disabled={importing || specFiles.length === 0}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-colors disabled:opacity-50"
          >
            {importing ? <IconLoader2 size={12} className="animate-spin" /> : <IconUpload size={12} />}
            Import {specFiles.length > 0 ? `${specFiles.length} Specs` : ""}
          </button>
        </div>
      </div>
    </div>
  );
}
