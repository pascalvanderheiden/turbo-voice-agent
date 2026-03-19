"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  IconMicrophone,
  IconBrain,
  IconNote,
  IconBulb,
  IconSearch,
  IconLoader2,
  IconRefresh,
  IconMessageCircle,
  IconCode,
  IconFileText,
  IconPackage,
  IconExternalLink,
  IconTrash,
  IconDownload,
  IconPlus,
  IconX,
  IconSettings,
  IconBrandGithub,
  IconServer,
  IconUpload,
} from "@tabler/icons-react";
import { agentsApi, notesApi, ideasApi, researchApi, specsApi, devApi, skillsApi, type AgentInfo, type AgentEdge, type InstalledSkill } from "@/lib/api";
import { SandboxConfig } from "@/components/agents/sandbox-config";
import { sandboxApi } from "@/lib/sandbox-api";
import { useI18n } from "@/lib/i18n";
import { useNotifications } from "@/lib/notifications";

interface MarketplaceSkill {
  name: string;
  description: string;
  url: string;
  repo?: string;
  skillDir?: string;
  installs?: number;
}

const AGENT_ICONS: Record<string, typeof IconBrain> = {
  voice: IconMicrophone,
  chat: IconMessageCircle,
  supervisor: IconBrain,
  notes: IconNote,
  brainstorm: IconBulb,
  research: IconSearch,
  spec: IconFileText,
  dev: IconCode,
  skills: IconSettings,
};

const AGENT_COLORS: Record<string, string> = {
  voice: "var(--color-brand-pink)",
  chat: "var(--color-brand-cyan)",
  supervisor: "var(--color-brand-purple)",
  notes: "var(--color-brand-cyan)",
  brainstorm: "var(--color-brand-purple)",
  research: "var(--color-brand-cyan)",
  spec: "var(--color-brand-purple)",
  dev: "var(--color-brand-pink)",
  skills: "var(--color-brand-cyan)",
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [edges, setEdges] = useState<AgentEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [skills, setSkills] = useState<InstalledSkill[]>([]);
  const [marketplaceSkills, setMarketplaceSkills] = useState<MarketplaceSkill[]>([]);
  const [skillSearch, setSkillSearch] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [installing, setInstalling] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sandboxStatus, setSandboxStatus] = useState<string>("loading");
  const [sandboxActiveTasks, setSandboxActiveTasks] = useState<number>(0);
  const [sandboxPremiumRequests, setSandboxPremiumRequests] = useState<number>(0);
  const sandboxPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { t } = useI18n();
  const { addNotification } = useNotifications();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [status, notesList, ideasList, researchList, specsList, devList, skillsResp] = await Promise.all([
        agentsApi.status(),
        notesApi.list().catch(() => []),
        ideasApi.list().catch(() => []),
        researchApi.list().catch(() => []),
        specsApi.list().catch(() => []),
        devApi.list().catch(() => []),
        skillsApi.listInstalled().catch(() => ({ skills: [] })),
      ]);
      setAgents(status.agents);
      setEdges(status.edges);
      setSkills(skillsResp.skills);
      setStats({
        notes: notesList.length,
        brainstorm: ideasList.length,
        research: researchList.length,
        spec: specsList.length,
        dev: devList.length,
      });
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshSkills = useCallback(async () => {
    try {
      const resp = await skillsApi.listInstalled();
      setSkills(resp.skills);
    } catch { /* ignore */ }
  }, []);

  // Debounced backend search
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!skillSearch.trim()) {
      setMarketplaceSkills([]);
      setSearchLoading(false);
      return;
    }
    setSearchLoading(true);
    searchTimer.current = setTimeout(async () => {
      try {
        const resp = await skillsApi.search(skillSearch);
        setMarketplaceSkills(resp.results || []);
      } catch {
        setMarketplaceSkills([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [skillSearch]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll sandbox status
  const fetchSandboxStatus = useCallback(async () => {
    try {
      const data = await sandboxApi.status();
      const raw = data.status || "not_configured";
      const tasks = data.activeTasks ?? 0;
      setSandboxActiveTasks(tasks);
      setSandboxPremiumRequests(data.premiumRequests ?? 0);
      setSandboxStatus(raw === "ready" && tasks > 0 ? "busy" : raw);
    } catch {
      setSandboxStatus("error");
    }
  }, []);

  useEffect(() => {
    fetchSandboxStatus();
    sandboxPollRef.current = setInterval(fetchSandboxStatus, 15_000);
    return () => {
      if (sandboxPollRef.current) clearInterval(sandboxPollRef.current);
    };
  }, [fetchSandboxStatus]);

  const handleActivate = async (skill: MarketplaceSkill) => {
    const repo = skill.repo || "";
    if (!repo) {
      addNotification("Activate failed: No repository info for this skill");
      return;
    }
    const skillDir = skill.skillDir || skill.name;
    const npxCommand = `npx -y degit ${repo}/${skillDir} .github/skills/${skillDir}`;
    setInstalling((prev) => new Set(prev).add(skill.name));
    addNotification(`Activating ${skill.name} from ${repo}...`);
    try {
      const result = await skillsApi.activate(repo, skillDir, npxCommand, skill.description || "");
      if (result.success) {
        addNotification(`Skill "${result.name || skill.name}" activated successfully`);
        await refreshSkills();
      } else {
        addNotification(`Activate failed: ${result.error || "Unknown error"}`);
      }
    } catch (e: unknown) {
      addNotification(`Activate failed: ${String(e)}`);
    } finally {
      setInstalling((prev) => { const next = new Set(prev); next.delete(skill.name); return next; });
    }
  };

  const handleDeactivate = async (name: string) => {
    setDeleteConfirm(null);
    setDeleting(name);
    try {
      await skillsApi.deactivate(name);
      addNotification(`Skill "${name}" deactivated`);
      await refreshSkills();
    } catch (e: unknown) {
      addNotification(`Deactivate failed: ${String(e)}`);
    } finally {
      setDeleting(null);
    }
  };

  const handleUploadLocal = async () => {
    if (!uploadName.trim() || uploadFiles.length === 0) return;
    setUploading(true);
    try {
      const result = await skillsApi.uploadLocal(uploadName.trim(), uploadFiles);
      if (result.success) {
        // Also activate the skill in Cosmos so it appears in the active list
        try {
          await skillsApi.activate("local", uploadName.trim(), "", `Local skill: ${uploadName.trim()}`);
        } catch {
          // Blob upload succeeded even if activation fails
        }
        addNotification(result.message);
        await refreshSkills();
        setUploadOpen(false);
        setUploadName("");
        setUploadFiles([]);
      }
    } catch (e: unknown) {
      addNotification(`Upload failed: ${String(e)}`);
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <IconLoader2 size={24} className="animate-spin text-[var(--color-text-muted)]" />
      </div>
    );
  }

  const gateways = agents.filter((a) => a.type === "gateway");
  const orchestrator = agents.find((a) => a.type === "orchestrator");
  const specialists = agents.filter((a) => a.type === "specialist");

  const filteredInstalled = skills.filter((s) =>
    !skillSearch || s.name.toLowerCase().includes(skillSearch.toLowerCase()) || s.description?.toLowerCase().includes(skillSearch.toLowerCase())
  );
  const availableMarketplace = marketplaceSkills.filter((ms) => !skills.some((is) => is.name === ms.name));

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold gradient-brand-text">{t("agents.title")}</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">{t("agents.subtitle")}</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius-md)] text-sm bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
        >
          <IconRefresh size={14} /> {t("agents.refresh")}
        </button>
      </div>

      {/* Architecture Diagram */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 overflow-hidden">
        <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-6">{t("agents.architecture")}</h2>
        <ArchitectureDiagram
          gateways={gateways}
          orchestrator={orchestrator}
          specialists={specialists}
          sandboxStatus={sandboxStatus}
          sandboxActiveTasks={sandboxActiveTasks}
          sandboxPremiumRequests={sandboxPremiumRequests}
        />
      </div>

      {/* Agent Detail Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => {
          const Icon = AGENT_ICONS[agent.id] || IconBrain;
          const color = AGENT_COLORS[agent.id] || "var(--color-text-muted)";
          const count = stats[agent.id];

          return (
            <div
              key={agent.id}
              className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-5 space-y-3"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="flex items-center justify-center w-10 h-10 rounded-[var(--radius-md)]"
                    style={{ backgroundColor: `${color}15`, color }}
                  >
                    <Icon size={20} stroke={1.5} />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">{agent.name}</h3>
                    <p className="text-xs text-[var(--color-text-muted)] capitalize">{agent.type}</p>
                  </div>
                </div>
                <StatusDot status={agent.status} />
              </div>

              {agent.model && (
                <div className="text-xs text-[var(--color-text-muted)]">
                  <span className="font-medium">{t("agents.model")}:</span> {agent.model}
                </div>
              )}

              {agent.mcpServers && agent.mcpServers.length > 0 && (
                <div className="text-xs text-[var(--color-text-muted)]">
                  <span className="font-medium">MCP:</span>{" "}
                  {agent.mcpServers.map((s) => (
                    <span
                      key={s}
                      className="inline-flex items-center gap-1 ml-1 px-1.5 py-0.5 rounded bg-[var(--color-brand-purple)]/10 text-[var(--color-brand-purple)] text-[10px] font-medium"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}

              {agent.tools && agent.tools.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-[var(--color-text-muted)]">{t("agents.tools")} ({agent.tools.length})</p>
                  <div className="flex flex-wrap gap-1">
                    {agent.tools.map((tool) => (
                      <span
                        key={tool}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]"
                      >
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {count !== undefined && (
                <div className="pt-2 border-t border-[var(--color-border-dark)]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--color-text-muted)]">{t("agents.items")}</span>
                    <span className="font-medium" style={{ color }}>{count}</span>
                  </div>
                </div>
              )}

              {agent.type === "orchestrator" && (
                <div className="pt-2 border-t border-[var(--color-border-dark)]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--color-text-muted)]">{t("agents.routing")}</span>
                    <span className="font-medium text-[var(--color-text-secondary)]">
                      {specialists.length} {t("agents.specialists")}
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Sandbox Config */}
      <SandboxConfig />

      {/* Skills Marketplace */}
      <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-sm font-medium text-[var(--color-text-muted)]">Skills Marketplace</h2>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{skills.length} activated</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setUploadOpen(true)}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-[var(--radius-md)] bg-[var(--color-brand-purple)]/10 text-[var(--color-brand-purple)] hover:bg-[var(--color-brand-purple)]/20 transition-colors"
            >
              <IconUpload size={13} />
              Upload Local
            </button>
            <div className="relative flex-1 min-w-0">
              <IconSearch size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
              <input
                type="text"
                placeholder="Search skills.sh..."
                value={skillSearch}
                onChange={(e) => setSkillSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-brand-pink)] transition-colors w-full sm:w-48"
              />
              {searchLoading && <IconLoader2 size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 animate-spin text-[var(--color-text-muted)]" />}
            </div>
          </div>
        </div>

        {/* Installed Skills */}
        {skills.length > 0 && (
          <div className="mb-4">
            <h3 className="text-xs font-medium text-green-400 mb-2 flex items-center gap-1.5">
              <IconPackage size={12} /> Active ({filteredInstalled.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredInstalled.map((skill) => (
                <div key={skill.name} className="p-3 rounded-[var(--radius-md)] border border-green-500/20 bg-green-500/5 group">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="font-medium text-sm truncate">{skill.name}</div>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-400 shrink-0">active</span>
                      {skill.source && (
                        <span className={`text-[9px] px-1.5 py-0.5 rounded-full shrink-0 ${
                          skill.source === "local"
                            ? "bg-[var(--color-brand-purple)]/15 text-[var(--color-brand-purple)]"
                            : "bg-[var(--color-brand-cyan)]/15 text-[var(--color-brand-cyan)]"
                        }`}>
                          {skill.source === "local" ? "local" : "marketplace"}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => setDeleteConfirm(skill.name)}
                      disabled={deleting === skill.name}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-[var(--color-text-muted)] hover:text-red-400 transition-all shrink-0"
                      title="Deactivate skill"
                    >
                      {deleting === skill.name ? <IconLoader2 size={13} className="animate-spin" /> : <IconTrash size={13} />}
                    </button>
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{skill.description || "No description"}</p>
                  {skill.source && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{skill.source}</p>}
                  {skill.activatedAt && <p className="text-[10px] text-[var(--color-text-muted)]">Activated {new Date(skill.activatedAt).toLocaleDateString()}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Marketplace Search Results */}
        {skillSearch && availableMarketplace.length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-[var(--color-brand-cyan)] mb-2 flex items-center gap-1.5">
              <IconExternalLink size={12} /> Available on skills.sh ({availableMarketplace.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {availableMarketplace.map((skill) => (
                <div
                  key={`${skill.repo}/${skill.name}`}
                  className="p-3 rounded-[var(--radius-md)] border border-[var(--color-border-dark)] bg-[var(--color-bg-tertiary)]"
                >
                  <div className="flex items-center justify-between">
                    <a
                      href={skill.url || `https://skills.sh/${skill.repo || ""}/${skill.name}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-sm hover:text-[var(--color-brand-cyan)] transition-colors flex items-center gap-1"
                    >
                      {skill.name}
                      <IconExternalLink size={11} className="text-[var(--color-text-muted)]" />
                    </a>
                    <button
                      onClick={() => handleActivate(skill)}
                      disabled={installing.has(skill.name)}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)] hover:bg-[var(--color-brand-cyan)]/20 transition-colors disabled:opacity-50"
                    >
                      {installing.has(skill.name) ? <IconLoader2 size={11} className="animate-spin" /> : <IconDownload size={11} />}
                      Activate
                    </button>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    {skill.repo && <span className="text-[10px] text-[var(--color-text-muted)]">{skill.repo}</span>}
                    {skill.installs != null && skill.installs > 0 && (
                      <span className="text-[10px] text-[var(--color-text-muted)]">
                        <IconDownload size={9} className="inline mr-0.5" />
                        {skill.installs >= 1000 ? `${(skill.installs / 1000).toFixed(1)}K` : skill.installs}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {skillSearch && !searchLoading && availableMarketplace.length === 0 && (
          <p className="text-xs text-[var(--color-text-muted)] text-center py-4">
            No marketplace results for &ldquo;{skillSearch}&rdquo;. Try a different search term.
          </p>
        )}

        {skills.length === 0 && !skillSearch && (
          <p className="text-sm text-[var(--color-text-muted)]">
            No skills activated. Search the marketplace above to find and activate skills.
          </p>
        )}
      </div>

      {/* Delete confirmation dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-sm mx-4">
            <h3 className="font-medium text-sm mb-2">Deactivate skill &ldquo;{deleteConfirm}&rdquo;?</h3>
            <p className="text-xs text-[var(--color-text-muted)] mb-4">
              This will deactivate the skill. You can re-activate it from the marketplace at any time.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeactivate(deleteConfirm)}
                className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
              >
                Deactivate
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload local skill dialog */}
      {uploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-sm">Upload Local Skill</h3>
              <button onClick={() => { setUploadOpen(false); setUploadName(""); setUploadFiles([]); }} className="p-1 hover:bg-[var(--color-bg-tertiary)] rounded">
                <IconX size={14} />
              </button>
            </div>
            <p className="text-xs text-[var(--color-text-muted)] mb-4">
              Upload a skill directory (SKILL.md + supporting files) to Azure Blob Storage.
              The skill will be available in sandbox containers on next startup.
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-[var(--color-text-muted)] mb-1 block">Skill Name</label>
                <input
                  type="text"
                  placeholder="my-custom-skill"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-brand-purple)] transition-colors"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--color-text-muted)] mb-1 block">Files (SKILL.md required)</label>
                <input
                  type="file"
                  multiple
                  accept=".md,.txt,.json,.yaml,.yml,.js,.ts,.py"
                  onChange={(e) => setUploadFiles(Array.from(e.target.files || []))}
                  className="w-full text-xs text-[var(--color-text-muted)] file:mr-3 file:py-1.5 file:px-3 file:rounded-[var(--radius-md)] file:border-0 file:text-xs file:font-medium file:bg-[var(--color-brand-purple)]/10 file:text-[var(--color-brand-purple)] hover:file:bg-[var(--color-brand-purple)]/20 file:cursor-pointer file:transition-colors"
                />
                {uploadFiles.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {uploadFiles.map((f) => (
                      <div key={f.name} className="text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
                        <IconFileText size={10} /> {f.name} ({(f.size / 1024).toFixed(1)} KB)
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setUploadOpen(false); setUploadName(""); setUploadFiles([]); }}
                className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUploadLocal}
                disabled={uploading || !uploadName.trim() || uploadFiles.length === 0}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-[var(--radius-md)] bg-[var(--color-brand-purple)]/10 text-[var(--color-brand-purple)] hover:bg-[var(--color-brand-purple)]/20 transition-colors disabled:opacity-50"
              >
                {uploading ? <IconLoader2 size={12} className="animate-spin" /> : <IconUpload size={12} />}
                Upload & Activate
              </button>
            </div>
          </div>
        </div>
      )}


    </div>
  );
}

function AgentNode({ agent, compact }: { agent: AgentInfo; compact?: boolean }) {
  const Icon = AGENT_ICONS[agent.id] || IconBrain;
  const color = AGENT_COLORS[agent.id] || "var(--color-text-muted)";

  return (
    <div
      className={`flex items-center gap-2 border rounded-[var(--radius-lg)] transition-colors shrink-0 ${
        compact ? "px-2.5 py-1.5" : "px-4 py-2.5"
      }`}
      style={{
        borderColor: `${color}40`,
        backgroundColor: `${color}08`,
      }}
    >
      <div
        className={`flex items-center justify-center rounded-[var(--radius-md)] ${compact ? "w-6 h-6" : "w-8 h-8"}`}
        style={{ backgroundColor: `${color}20`, color }}
      >
        <Icon size={compact ? 13 : 16} stroke={1.5} />
      </div>
      <div className="min-w-0">
        <p className={`font-medium truncate ${compact ? "text-[11px]" : "text-sm"}`} style={{ color }}>
          {agent.name}
        </p>
        {!compact && agent.model && (
          <p className="text-[10px] text-[var(--color-text-muted)] truncate">{agent.model}</p>
        )}
      </div>
      <StatusDot status={agent.status} />
    </div>
  );
}

interface ConnectorPath {
  d: string;
  dashed?: boolean;
  color?: string;
}

function ArchitectureDiagram({
  gateways,
  orchestrator,
  specialists,
  sandboxStatus,
  sandboxActiveTasks,
  sandboxPremiumRequests,
}: {
  gateways: AgentInfo[];
  orchestrator: AgentInfo | undefined;
  specialists: AgentInfo[];
  sandboxStatus: string;
  sandboxActiveTasks: number;
  sandboxPremiumRequests: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const [paths, setPaths] = useState<ConnectorPath[]>([]);

  const setRef = useCallback(
    (id: string) => (el: HTMLDivElement | null) => {
      if (el) nodeRefs.current.set(id, el);
      else nodeRefs.current.delete(id);
    },
    [],
  );

  useEffect(() => {
    const updatePaths = () => {
      const container = containerRef.current;
      if (!container) return;
      const cRect = container.getBoundingClientRect();

      const getRect = (id: string) => {
        const el = nodeRefs.current.get(id);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {
          cx: r.left + r.width / 2 - cRect.left,
          top: r.top - cRect.top,
          bottom: r.bottom - cRect.top,
        };
      };

      const newPaths: ConnectorPath[] = [];
      const sup = getRect("supervisor");

      // Gateways → Supervisor (smooth S-curve)
      for (const gw of gateways) {
        const from = getRect(gw.id);
        if (from && sup) {
          const midY = (from.bottom + sup.top) / 2;
          newPaths.push({
            d: `M${from.cx},${from.bottom} C${from.cx},${midY} ${sup.cx},${midY} ${sup.cx},${sup.top}`,
          });
        }
      }

      // Supervisor → each specialist (smooth bezier fan-out)
      for (const spec of specialists) {
        const to = getRect(spec.id);
        if (sup && to) {
          const dy = to.top - sup.bottom;
          const cp1y = sup.bottom + dy * 0.35;
          const cp2y = sup.bottom + dy * 0.65;
          newPaths.push({
            d: `M${sup.cx},${sup.bottom} C${sup.cx},${cp1y} ${to.cx},${cp2y} ${to.cx},${to.top}`,
          });
        }
      }

      // Dev → Sandbox (dashed cyan curve)
      const dev = getRect("dev");
      const sandbox = getRect("sandbox");
      if (dev && sandbox) {
        const dy = sandbox.top - dev.bottom;
        const cp1y = dev.bottom + dy * 0.35;
        const cp2y = dev.bottom + dy * 0.65;
        newPaths.push({
          d: `M${dev.cx},${dev.bottom} C${dev.cx},${cp1y} ${sandbox.cx},${cp2y} ${sandbox.cx},${sandbox.top}`,
          dashed: true,
          color: "var(--color-brand-cyan)",
        });
      }

      setPaths(newPaths);
    };

    // Measure after layout settles
    const raf = requestAnimationFrame(updatePaths);
    const observer = new ResizeObserver(updatePaths);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [gateways, specialists]);

  return (
    <div ref={containerRef} className="relative">
      {/* SVG connector overlay */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
        <defs>
          <marker id="conn-arrow" markerWidth="4" markerHeight="4" refX="3.5" refY="2" orient="auto">
            <path d="M0,0.5 L3.5,2 L0,3.5" fill="none" stroke="var(--color-text-muted)" strokeWidth="0.7" />
          </marker>
          <marker id="conn-arrow-cyan" markerWidth="4" markerHeight="4" refX="3.5" refY="2" orient="auto">
            <path d="M0,0.5 L3.5,2 L0,3.5" fill="none" stroke="var(--color-brand-cyan)" strokeWidth="0.7" />
          </marker>
        </defs>
        {paths.map((p, i) => (
          <path
            key={i}
            d={p.d}
            stroke={p.color || "var(--color-text-muted)"}
            strokeWidth="1"
            fill="none"
            opacity="0.45"
            strokeDasharray={p.dashed ? "4 3" : undefined}
            markerEnd={p.color ? "url(#conn-arrow-cyan)" : "url(#conn-arrow)"}
          />
        ))}
      </svg>

      {/* Node layout */}
      <div className="flex flex-col items-center gap-8 relative" style={{ zIndex: 1 }}>
        {/* Gateways row */}
        <div className="flex items-center justify-center gap-4 flex-wrap">
          {gateways.map((gw) => (
            <div key={gw.id} ref={setRef(gw.id)}>
              <AgentNode agent={gw} />
            </div>
          ))}
        </div>

        {/* Supervisor */}
        {orchestrator && (
          <div ref={setRef("supervisor")}>
            <AgentNode agent={orchestrator} />
          </div>
        )}

        {/* Specialists - 2 rows of 4 */}
        <div className="flex flex-wrap justify-center gap-3 max-w-3xl">
          {specialists.map((s) => (
            <div key={s.id} ref={setRef(s.id)} className="flex flex-col items-center">
              <AgentNode agent={s} compact />
              {s.id === "dev" && (
                <div ref={setRef("sandbox")} className="mt-3">
                  <SandboxNodeInline status={sandboxStatus} activeTasks={sandboxActiveTasks} premiumRequests={sandboxPremiumRequests} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const isOnline = status === "online";
  return (
    <div className="flex items-center gap-1 shrink-0" title={status}>
      <div
        className={`w-2 h-2 rounded-full ${
          isOnline ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.4)]" : "bg-red-500"
        }`}
      />
    </div>
  );
}

const SANDBOX_STATUS: Record<string, { dot: string; pulse?: boolean }> = {
  ready:          { dot: "bg-green-400" },
  busy:           { dot: "bg-yellow-400", pulse: true },
  provisioning:   { dot: "bg-yellow-400", pulse: true },
  stopped:        { dot: "bg-[var(--color-text-muted)]" },
  error:          { dot: "bg-red-400" },
  not_configured: { dot: "bg-[var(--color-text-muted)]" },
  loading:        { dot: "bg-[var(--color-text-muted)]" },
};

function SandboxNodeInline({ status, activeTasks, premiumRequests }: { status: string; activeTasks: number; premiumRequests: number }) {
  const cfg = SANDBOX_STATUS[status] || SANDBOX_STATUS.not_configured;
  const label = status === "not_configured"
    ? "Not Configured"
    : status === "busy"
      ? `Busy (${activeTasks})`
      : status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <div
      className="flex items-center gap-2 px-2.5 py-1.5 rounded-[var(--radius-lg)] border border-dashed shrink-0"
      style={{
        borderColor: "var(--color-brand-cyan)",
        backgroundColor: "color-mix(in srgb, var(--color-brand-cyan) 5%, transparent)",
      }}
    >
      <div
        className="flex items-center justify-center w-6 h-6 rounded-[var(--radius-md)]"
        style={{ backgroundColor: "color-mix(in srgb, var(--color-brand-cyan) 15%, transparent)" }}
      >
        <IconServer size={13} stroke={1.5} className="text-[var(--color-brand-cyan)]" />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-[var(--color-brand-cyan)] truncate flex items-center gap-1">
          <IconBrandGithub size={10} stroke={1.5} />
          Copilot CLI Sandbox
        </p>
        {premiumRequests > 0 && (
          <p className="text-[9px] text-[var(--color-brand-pink)] font-medium">
            {premiumRequests.toLocaleString()} premium req.
          </p>
        )}
      </div>
      <span className="relative flex h-2 w-2 shrink-0" title={label}>
        {cfg.pulse && (
          <span className={`absolute inset-0 rounded-full ${cfg.dot} opacity-75 animate-ping`} />
        )}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${cfg.dot}`} />
      </span>
    </div>
  );
}
