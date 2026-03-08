import { useCallback, useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, Linking, TouchableOpacity } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { researchApi, type Research } from "@/lib/api";
import { colors } from "@/lib/theme";

export default function ResearchDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [research, setResearch] = useState<Research | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setResearch(await researchApi.get(id));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Poll if pending
  useEffect(() => {
    if (research?.status !== "pending") return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [research?.status, load]);

  if (loading || !research) {
    return (
      <View style={styles.center}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  const isPending = research.status === "pending";
  const isFailed = research.status === "failed";

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>{research.title}</Text>
        <View style={styles.meta}>
          <View style={[styles.badge, { backgroundColor: research.mode === "deep_research" ? `${colors.brand.purple}20` : `${colors.brand.cyan}20` }]}>
            <Text style={[styles.badgeText, { color: research.mode === "deep_research" ? colors.brand.purple : colors.brand.cyan }]}>
              {research.mode === "deep_research" ? "Deep Research" : "Web Search"}
            </Text>
          </View>
          <View style={[styles.badge, {
            backgroundColor: isPending ? "#F59E0B20" : isFailed ? "#EF444420" : "#10B98120",
          }]}>
            <Text style={[styles.badgeText, {
              color: isPending ? "#F59E0B" : isFailed ? "#EF4444" : "#10B981",
            }]}>
              {research.status}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Query</Text>
        <Text style={styles.queryText}>{research.query}</Text>
      </View>

      {isPending && (
        <View style={styles.pendingBox}>
          <Ionicons name="time-outline" size={20} color="#F59E0B" />
          <Text style={styles.pendingText}>Research is in progress... results will appear here when ready.</Text>
        </View>
      )}

      {isFailed && research.error && (
        <View style={styles.errorBox}>
          <Ionicons name="alert-circle-outline" size={20} color="#EF4444" />
          <Text style={styles.errorText}>{research.error}</Text>
        </View>
      )}

      {research.result && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Results</Text>
          <Text style={styles.resultText}>{research.result}</Text>
        </View>
      )}

      {research.citations && research.citations.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Sources ({research.citations.length})</Text>
          {research.citations.map((c, i) => (
            <TouchableOpacity key={i} style={styles.citation} onPress={() => Linking.openURL(c.url)}>
              <Ionicons name="link-outline" size={14} color={colors.brand.cyan} />
              <Text style={styles.citationText} numberOfLines={1}>{c.title || c.url}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.dark.bgPrimary },
  loadingText: { color: colors.dark.textMuted },
  header: { marginBottom: 20 },
  title: { fontSize: 22, fontWeight: "700", color: colors.dark.textPrimary, marginBottom: 10 },
  meta: { flexDirection: "row", gap: 8 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  badgeText: { fontSize: 12, fontWeight: "600" },
  section: { marginBottom: 20 },
  sectionLabel: { fontSize: 13, fontWeight: "600", color: colors.dark.textMuted, marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 },
  queryText: { fontSize: 15, color: colors.dark.textSecondary, lineHeight: 22 },
  resultText: { fontSize: 15, color: colors.dark.textPrimary, lineHeight: 24 },
  pendingBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#F59E0B10",
    padding: 14,
    borderRadius: 10,
    marginBottom: 20,
  },
  pendingText: { flex: 1, fontSize: 14, color: "#F59E0B" },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#EF444410",
    padding: 14,
    borderRadius: 10,
    marginBottom: 20,
  },
  errorText: { flex: 1, fontSize: 14, color: "#EF4444" },
  citation: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.dark.border,
  },
  citationText: { fontSize: 14, color: colors.brand.cyan, flex: 1 },
});
