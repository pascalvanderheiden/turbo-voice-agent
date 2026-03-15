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
  IconFolderPlus,
  IconX,
  IconSettings,
  IconBrandGithub,
  IconServer,
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
  const [showLocalDialog, setShowLocalDialog] = useState(false);
  const [localFiles, setLocalFiles] = useState<FileList | null>(null);
  const [localName, setLocalName] = useState("");
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sandboxStatus, setSandboxStatus] = useState<string>("loading");
  const [sandboxActiveTasks, setSandboxActiveTasks] = useState<number>(0);
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

  const handleInstall = async (skill: MarketplaceSkill) => {
    const repo = skill.repo || "";
    if (!repo) {
      addNotification("Install failed: No repository info for this skill");
      return;
    }
    setInstalling((prev) => new Set(prev).add(skill.name));
    addNotification(`Installing ${skill.name} from ${repo}...`);
    try {
      // Pass skillDir as skillName — empty string means install whole repo
      const result = await skillsApi.install(repo, skill.skillDir || "");
      if (result.status === "installed") {
        addNotification(`Skill "${result.name || skill.name}" installed successfully`);
        await refreshSkills();
      } else {
        addNotification(`Install failed: ${result.error || "Unknown error"}`);
      }
    } catch (e: unknown) {
      addNotification(`Install failed: ${String(e)}`);
    } finally {
      setInstalling((prev) => { const next = new Set(prev); next.delete(skill.name); return next; });
    }
  };

  const handleDelete = async (name: string) => {
    setDeleteConfirm(null);
    setDeleting(name);
    try {
      await skillsApi.delete(name);
      addNotification(`Skill "${name}" deleted`);
      await refreshSkills();
    } catch (e: unknown) {
      addNotification(`Delete failed: ${String(e)}`);
    } finally {
      setDeleting(null);
    }
  };

  const handleLocalInstall = async () => {
    if (!localFiles || !localName) return;
    setShowLocalDialog(false);
    addNotification(`Installing local skill "${localName}"...`);
    try {
      const result = await skillsApi.uploadLocal(localName, localFiles);
      if (result.status === "installed") {
        addNotification(`Skill "${localName}" installed successfully`);
        await refreshSkills();
      } else {
        addNotification(`Install failed: ${result.error || "Unknown error"}`);
      }
    } catch (e: unknown) {
      addNotification(`Install failed: ${String(e)}`);
    }
    setLocalFiles(null);
    setLocalName("");
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

        <div className="flex flex-col items-center gap-2 min-w-0">
          {/* Gateways row */}
          <div className="flex items-center justify-center gap-4 flex-wrap">
            {gateways.map((gw) => (
              <AgentNode key={gw.id} agent={gw} />
            ))}
          </div>

          <FlowArrow />

          {/* Supervisor */}
          {orchestrator && <AgentNode agent={orchestrator} />}

          {/* Fan-out to specialists */}
          <div className="w-full flex justify-center pt-1">
            <div className="relative w-full max-w-2xl">
              {/* SVG fan-out: vertical drop → horizontal bar → branches */}
              <svg width="100%" height={20} className="overflow-visible" preserveAspectRatio="none">
                <defs>
                  <marker id="fan-arrow" markerWidth="4" markerHeight="4" refX="3.5" refY="2" orient="auto">
                    <path d="M0,0 L4,2 L0,4" fill="none" stroke="var(--color-text-muted)" strokeWidth="0.8" />
                  </marker>
                </defs>
                <line x1="50%" y1="0" x2="50%" y2="10" stroke="var(--color-text-muted)" strokeWidth="1.5" opacity="0.6" />
                <line x1="5%" y1="10" x2="95%" y2="10" stroke="var(--color-text-muted)" strokeWidth="1.5" opacity="0.6" />
              </svg>
              <div className="flex flex-wrap justify-center gap-3 mt-0 px-2">
                {specialists.map((s) => (
                  <div key={s.id} className="flex flex-col items-center">
                    <svg width={20} height={18} className="overflow-visible">
                      <path d="M10,0 C10,6 10,12 10,14" stroke="var(--color-text-muted)" strokeWidth="1.5"
                        fill="none" opacity="0.6" markerEnd="url(#fan-arrow)" />
                    </svg>
                    <AgentNode agent={s} compact />
                    {/* Sandbox node below the Dev agent */}
                    {s.id === "dev" && (
                      <SandboxNode status={sandboxStatus} activeTasks={sandboxActiveTasks} />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
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
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{skills.length} installed</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowLocalDialog(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] transition-colors shrink-0"
            >
              <IconFolderPlus size={13} /> Add Local
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
              <IconPackage size={12} /> Installed ({filteredInstalled.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredInstalled.map((skill) => (
                <div key={skill.name} className="p-3 rounded-[var(--radius-md)] border border-green-500/20 bg-green-500/5 group">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="font-medium text-sm truncate">{skill.name}</div>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-400 shrink-0">installed</span>
                      {skill.source === "skills.sh" ? (
                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--color-brand-cyan)]/15 text-[var(--color-brand-cyan)] shrink-0">skills.sh</span>
                      ) : (
                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--color-brand-purple)]/15 text-[var(--color-brand-purple)] shrink-0">local</span>
                      )}
                    </div>
                    <button
                      onClick={() => setDeleteConfirm(skill.name)}
                      disabled={deleting === skill.name}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-[var(--color-text-muted)] hover:text-red-400 transition-all shrink-0"
                      title="Delete skill"
                    >
                      {deleting === skill.name ? <IconLoader2 size={13} className="animate-spin" /> : <IconTrash size={13} />}
                    </button>
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1 line-clamp-2">{skill.description || "No description"}</p>
                  {skill.version && <p className="text-[10px] text-[var(--color-text-muted)] mt-1">v{skill.version}</p>}
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
                      onClick={() => handleInstall(skill)}
                      disabled={installing.has(skill.name)}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded bg-[var(--color-brand-cyan)]/10 text-[var(--color-brand-cyan)] hover:bg-[var(--color-brand-cyan)]/20 transition-colors disabled:opacity-50"
                    >
                      {installing.has(skill.name) ? <IconLoader2 size={11} className="animate-spin" /> : <IconDownload size={11} />}
                      Install
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
            No skills installed. Search the marketplace above or click &quot;Add Local&quot; to install from a local directory.
          </p>
        )}
      </div>

      {/* Delete confirmation dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-sm mx-4">
            <h3 className="font-medium text-sm mb-2">Delete skill &ldquo;{deleteConfirm}&rdquo;?</h3>
            <p className="text-xs text-[var(--color-text-muted)] mb-4">
              This will remove the skill directory from .agents/skills/. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Local Skill dialog */}
      {showLocalDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] rounded-[var(--radius-lg)] p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-sm">Add Local Skill</h3>
              <button onClick={() => { setShowLocalDialog(false); setLocalFiles(null); setLocalName(""); }} className="p-1 rounded hover:bg-[var(--color-bg-tertiary)]">
                <IconX size={14} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-[var(--color-text-muted)] block mb-1">Skill Folder</label>
                <input
                  ref={folderInputRef}
                  type="file"
                  className="hidden"
                  onChange={(e) => {
                    const files = e.target.files;
                    if (files && files.length > 0) {
                      setLocalFiles(files);
                      // Derive skill name from folder name (webkitRelativePath = "folder/file.md")
                      const first = (files[0] as unknown as { webkitRelativePath?: string }).webkitRelativePath || files[0].name;
                      const folderName = first.split("/")[0] || "skill";
                      setLocalName(folderName);
                    }
                  }}
                />
                <button
                  onClick={() => {
                    // Set webkitdirectory attribute dynamically (TypeScript doesn't know it)
                    if (folderInputRef.current) {
                      folderInputRef.current.setAttribute("webkitdirectory", "");
                      folderInputRef.current.setAttribute("directory", "");
                      folderInputRef.current.click();
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 px-3 py-3 text-sm rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-dashed border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:border-[var(--color-brand-pink)] hover:text-[var(--color-brand-pink)] transition-colors cursor-pointer"
                >
                  <IconFolderPlus size={16} />
                  {localFiles ? `${localFiles.length} files selected` : "Browse folder..."}
                </button>
                <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Select a folder containing a SKILL.md file</p>
              </div>
              {localName && (
                <div>
                  <label className="text-xs font-medium text-[var(--color-text-muted)] block mb-1">Skill Name</label>
                  <input
                    type="text"
                    value={localName}
                    onChange={(e) => setLocalName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border-dark)] text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-brand-pink)]"
                  />
                  <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Auto-filled from folder name — edit if needed</p>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setShowLocalDialog(false); setLocalFiles(null); setLocalName(""); }}
                className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleLocalInstall}
                disabled={!localFiles || !localName}
                className="px-3 py-1.5 text-xs rounded-[var(--radius-md)] bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] hover:bg-[var(--color-brand-pink)]/20 transition-colors disabled:opacity-50"
              >
                <IconPlus size={12} className="inline mr-1" />
                Install
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

function FlowArrow() {
  return (
    <svg width={20} height={28} className="overflow-visible">
      <defs>
        <marker id="flow-arrow" markerWidth="4" markerHeight="4" refX="3.5" refY="2" orient="auto">
          <path d="M0,0 L4,2 L0,4" fill="none" stroke="var(--color-text-muted)" strokeWidth="0.8" />
        </marker>
      </defs>
      <path d="M10,0 C10,10 10,18 10,24" stroke="var(--color-text-muted)" strokeWidth="1.5"
        fill="none" opacity="0.6" markerEnd="url(#flow-arrow)" />
    </svg>
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

function SandboxNode({ status, activeTasks }: { status: string; activeTasks: number }) {
  const cfg = SANDBOX_STATUS[status] || SANDBOX_STATUS.not_configured;
  const label = status === "not_configured"
    ? "Not Configured"
    : status === "busy"
      ? `Busy (${activeTasks})`
      : status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <div className="flex flex-col items-center mt-0.5">
      <svg width={20} height={18} className="overflow-visible">
        <defs>
          <marker id="sandbox-arrow" markerWidth="4" markerHeight="4" refX="3.5" refY="2" orient="auto">
            <path d="M0,0 L4,2 L0,4" fill="none" stroke="var(--color-brand-cyan)" strokeWidth="0.8" />
          </marker>
        </defs>
        <path d="M10,0 C10,6 10,12 10,14" stroke="var(--color-brand-cyan)" strokeWidth="1.5"
          fill="none" opacity="0.6" markerEnd="url(#sandbox-arrow)" />
      </svg>
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
        </div>
        <span className="relative flex h-2 w-2 shrink-0" title={label}>
          {cfg.pulse && (
            <span className={`absolute inset-0 rounded-full ${cfg.dot} opacity-75 animate-ping`} />
          )}
          <span className={`relative inline-flex h-2 w-2 rounded-full ${cfg.dot}`} />
        </span>
      </div>
    </div>
  );
}
