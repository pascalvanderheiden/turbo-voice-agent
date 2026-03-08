import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { researchApi, type Research } from "@/lib/api";
import { colors } from "@/lib/theme";

const statusConfig = {
  pending: { color: "#F59E0B", icon: "time-outline" as const, label: "Pending" },
  completed: { color: "#10B981", icon: "checkmark-circle-outline" as const, label: "Completed" },
  failed: { color: "#EF4444", icon: "alert-circle-outline" as const, label: "Failed" },
};

export default function ResearchListScreen() {
  const [items, setItems] = useState<Research[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setItems(await researchApi.list());
    } catch {
      Alert.alert("Error", "Failed to load research");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Poll for pending items
  useEffect(() => {
    const hasPending = items.some((r) => r.status === "pending");
    if (!hasPending) return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [items, load]);

  const handleDelete = (item: Research) => {
    Alert.alert("Delete Research", `Delete "${item.title}"?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          await researchApi.delete(item.id);
          load();
        },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={load} tintColor={colors.brand.purple} />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Ionicons name="search-outline" size={48} color={colors.dark.textMuted} />
              <Text style={styles.emptyText}>No research yet</Text>
              <Text style={styles.emptySubtext}>Start research via voice or web search</Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => {
          const st = statusConfig[item.status];
          return (
            <TouchableOpacity
              style={styles.card}
              onPress={() => router.push({ pathname: "/research-detail", params: { id: item.id } })}
              onLongPress={() => handleDelete(item)}
            >
              <View style={styles.cardHeader}>
                <View style={[styles.modeBadge, item.mode === "deep_research" ? styles.deepBadge : styles.webBadge]}>
                  <Ionicons
                    name={item.mode === "deep_research" ? "telescope-outline" : "globe-outline"}
                    size={12}
                    color={item.mode === "deep_research" ? colors.brand.purple : colors.brand.cyan}
                  />
                  <Text style={[styles.modeText, { color: item.mode === "deep_research" ? colors.brand.purple : colors.brand.cyan }]}>
                    {item.mode === "deep_research" ? "Deep" : "Web"}
                  </Text>
                </View>
                <View style={[styles.statusDot, { backgroundColor: st.color }]} />
              </View>
              <Text style={styles.cardTitle} numberOfLines={1}>{item.title}</Text>
              <Text style={styles.cardQuery} numberOfLines={2}>{item.query}</Text>
              <View style={styles.cardFooter}>
                <Text style={styles.dateText}>{new Date(item.createdAt).toLocaleDateString()}</Text>
                <View style={styles.statusRow}>
                  <Ionicons name={st.icon} size={14} color={st.color} />
                  <Text style={[styles.statusLabel, { color: st.color }]}>{st.label}</Text>
                </View>
              </View>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  list: { padding: 16, gap: 12 },
  card: {
    padding: 16,
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.dark.border,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  modeBadge: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  webBadge: { backgroundColor: `${colors.brand.cyan}15` },
  deepBadge: { backgroundColor: `${colors.brand.purple}15` },
  modeText: { fontSize: 11, fontWeight: "600" },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  cardTitle: { fontSize: 16, fontWeight: "600", color: colors.dark.textPrimary, marginBottom: 4 },
  cardQuery: { fontSize: 14, color: colors.dark.textSecondary, marginBottom: 8 },
  cardFooter: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  dateText: { fontSize: 12, color: colors.dark.textMuted },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  statusLabel: { fontSize: 12, fontWeight: "500" },
  empty: { alignItems: "center", paddingTop: 100, gap: 8 },
  emptyText: { fontSize: 16, color: colors.dark.textSecondary },
  emptySubtext: { fontSize: 13, color: colors.dark.textMuted },
});
