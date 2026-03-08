import { useCallback, useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, RefreshControl, TouchableOpacity, Alert, TextInput } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { agentsApi, skillsApi, type AgentStatus, type AgentInfo, type InstalledSkill } from "@/lib/api";
import { colors } from "@/lib/theme";

const typeConfig = {
  gateway: { color: colors.brand.pink, icon: "radio-outline" as const, label: "Gateway" },
  orchestrator: { color: colors.brand.purple, icon: "git-network-outline" as const, label: "Orchestrator" },
  specialist: { color: colors.brand.cyan, icon: "construct-outline" as const, label: "Specialist" },
};

export default function AgentsScreen() {
  const [data, setData] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [skills, setSkills] = useState<InstalledSkill[]>([]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [status, skillsResp] = await Promise.all([
        agentsApi.status(),
        skillsApi.listInstalled().catch(() => ({ skills: [] })),
      ]);
      setData(status);
      setSkills(skillsResp.skills);
    } catch {
      // Agents endpoint might not be available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const agents = data?.agents || [];
  const edges = data?.edges || [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor="#F59E0B" />}
    >
      <Text style={styles.heading}>Agent Topology</Text>
      <Text style={styles.subtitle}>{agents.length} agents deployed</Text>

      {/* Flow diagram */}
      <View style={styles.flowContainer}>
        {agents.map((agent, idx) => {
          const cfg = typeConfig[agent.type] || typeConfig.specialist;
          const outEdges = edges.filter((e) => e.from === agent.id);
          return (
            <View key={agent.id}>
              <AgentNode agent={agent} config={cfg} />
              {outEdges.length > 0 && (
                <View style={styles.connector}>
                  <View style={styles.connectorLine} />
                  <Ionicons name="chevron-down" size={16} color={colors.dark.textMuted} />
                </View>
              )}
            </View>
          );
        })}
      </View>

      {/* Agent details */}
      <Text style={styles.sectionLabel}>Agent Details</Text>
      {agents.map((agent) => {
        const cfg = typeConfig[agent.type] || typeConfig.specialist;
        return (
          <View key={agent.id} style={styles.detailCard}>
            <View style={styles.detailHeader}>
              <View style={[styles.detailIcon, { backgroundColor: `${cfg.color}20` }]}>
                <Ionicons name={cfg.icon} size={18} color={cfg.color} />
              </View>
              <View style={styles.detailInfo}>
                <Text style={styles.detailName}>{agent.name}</Text>
                <Text style={styles.detailType}>{cfg.label}</Text>
              </View>
              <View style={[styles.statusIndicator, { backgroundColor: agent.status === "active" ? "#10B981" : "#F59E0B" }]} />
            </View>
            {agent.model && (
              <Text style={styles.detailModel}>Model: {agent.model}</Text>
            )}
            {agent.tools && agent.tools.length > 0 && (
              <View style={styles.toolsRow}>
                {agent.tools.map((tool) => (
                  <View key={tool} style={styles.toolChip}>
                    <Text style={styles.toolText}>{tool}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        );
      })}
      {/* Skills Management */}
      <Text style={styles.sectionLabel}>Installed Skills</Text>
      {skills.length === 0 ? (
        <Text style={styles.emptyText}>No skills installed</Text>
      ) : (
        skills.map((skill) => (
          <View key={skill.name} style={styles.skillCard}>
            <View style={styles.skillHeader}>
              <View style={{ flex: 1 }}>
                <Text style={styles.skillName}>{skill.name}</Text>
                <Text style={styles.skillDesc} numberOfLines={2}>{skill.description || "No description"}</Text>
              </View>
              <TouchableOpacity
                style={styles.deleteBtn}
                onPress={() => {
                  Alert.alert("Delete Skill", `Remove "${skill.name}"?`, [
                    { text: "Cancel", style: "cancel" },
                    {
                      text: "Delete", style: "destructive",
                      onPress: async () => {
                        try {
                          await skillsApi.delete(skill.name);
                          load();
                        } catch { Alert.alert("Error", "Failed to delete skill"); }
                      },
                    },
                  ]);
                }}
              >
                <Ionicons name="trash-outline" size={16} color="#EF4444" />
              </TouchableOpacity>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}

function AgentNode({ agent, config }: { agent: AgentInfo; config: { color: string; icon: keyof typeof Ionicons.glyphMap; label: string } }) {
  return (
    <View style={[styles.node, { borderColor: `${config.color}60` }]}>
      <View style={[styles.nodeIcon, { backgroundColor: `${config.color}20` }]}>
        <Ionicons name={config.icon} size={20} color={config.color} />
      </View>
      <View>
        <Text style={styles.nodeName}>{agent.name}</Text>
        <Text style={[styles.nodeType, { color: config.color }]}>{config.label}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  content: { padding: 16, paddingBottom: 40 },
  heading: { fontSize: 24, fontWeight: "700", color: colors.dark.textPrimary },
  subtitle: { fontSize: 14, color: colors.dark.textMuted, marginBottom: 20 },
  flowContainer: { alignItems: "center", marginBottom: 30 },
  node: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    minWidth: 200,
  },
  nodeIcon: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  nodeName: { fontSize: 15, fontWeight: "600", color: colors.dark.textPrimary },
  nodeType: { fontSize: 12, fontWeight: "500" },
  connector: { alignItems: "center", paddingVertical: 4 },
  connectorLine: { width: 2, height: 12, backgroundColor: colors.dark.border },
  sectionLabel: { fontSize: 13, fontWeight: "600", color: colors.dark.textMuted, marginBottom: 12, textTransform: "uppercase", letterSpacing: 0.5 },
  detailCard: {
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.dark.border,
    marginBottom: 10,
  },
  detailHeader: { flexDirection: "row", alignItems: "center", gap: 12 },
  detailIcon: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center" },
  detailInfo: { flex: 1 },
  detailName: { fontSize: 15, fontWeight: "600", color: colors.dark.textPrimary },
  detailType: { fontSize: 12, color: colors.dark.textMuted },
  statusIndicator: { width: 10, height: 10, borderRadius: 5 },
  detailModel: { fontSize: 13, color: colors.dark.textSecondary, marginTop: 8 },
  toolsRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 8 },
  toolChip: { backgroundColor: colors.dark.bgTertiary, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  toolText: { fontSize: 11, color: colors.dark.textSecondary },
  emptyText: { fontSize: 13, color: colors.dark.textMuted, textAlign: "center", paddingVertical: 20 },
  skillCard: {
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#22C55E30",
    marginBottom: 10,
  },
  skillHeader: { flexDirection: "row", alignItems: "center", gap: 12 },
  skillName: { fontSize: 15, fontWeight: "600", color: colors.dark.textPrimary },
  skillDesc: { fontSize: 12, color: colors.dark.textMuted, marginTop: 2 },
  deleteBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#EF444415",
    alignItems: "center",
    justifyContent: "center",
  },
});
