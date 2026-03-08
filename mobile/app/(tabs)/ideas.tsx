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
import { ideasApi, type Idea } from "@/lib/api";
import { colors } from "@/lib/theme";

export default function IdeasScreen() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [refining, setRefining] = useState<string | null>(null);
  const router = useRouter();

  const loadIdeas = useCallback(async () => {
    try {
      setLoading(true);
      const data = await ideasApi.list();
      setIdeas(data);
    } catch {
      Alert.alert("Error", "Failed to load ideas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadIdeas(); }, [loadIdeas]);

  const handleRefine = async (idea: Idea) => {
    setRefining(idea.id);
    try {
      await ideasApi.refine(idea.id);
      await loadIdeas();
      Alert.alert("Refined", `"${idea.title}" has been refined by AI`);
    } catch {
      Alert.alert("Error", "Failed to refine idea");
    } finally {
      setRefining(null);
    }
  };

  const handleDelete = (idea: Idea) => {
    Alert.alert("Delete Idea", `Delete "${idea.title}"?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          await ideasApi.delete(idea.id);
          loadIdeas();
        },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={ideas}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={loadIdeas} tintColor={colors.brand.cyan} />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Ionicons name="bulb-outline" size={48} color={colors.dark.textMuted} />
              <Text style={styles.emptyText}>No ideas yet</Text>
              <Text style={styles.emptySubtext}>Capture your first idea or brainstorm via voice</Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              router.push({
                pathname: "/idea-form",
                params: { id: item.id, title: item.title, description: item.description },
              })
            }
            onLongPress={() => handleDelete(item)}
          >
            <View style={styles.cardHeader}>
              <View style={styles.titleRow}>
                <Text style={styles.cardTitle} numberOfLines={1}>{item.title}</Text>
                <View style={[styles.statusBadge, item.status === "refined" ? styles.refinedBadge : styles.draftBadge]}>
                  <Text style={styles.statusText}>{item.status}</Text>
                </View>
              </View>
            </View>
            <Text style={styles.cardDesc} numberOfLines={3}>{item.description}</Text>
            {item.refinedDraft && (
              <View style={styles.refinedBox}>
                <Text style={styles.refinedLabel}>✨ Refined</Text>
                <Text style={styles.refinedText}>{item.refinedDraft}</Text>
              </View>
            )}
            <View style={styles.cardFooter}>
              <Text style={styles.dateText}>
                {new Date(item.updatedAt).toLocaleDateString()}
              </Text>
              <TouchableOpacity
                style={styles.refineBtn}
                onPress={() => handleRefine(item)}
                disabled={refining === item.id}
              >
                <Ionicons name="sparkles-outline" size={16} color={colors.brand.cyan} />
                <Text style={styles.refineBtnText}>
                  {refining === item.id ? "Refining..." : "Refine"}
                </Text>
              </TouchableOpacity>
            </View>
          </TouchableOpacity>
        )}
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push("/idea-form")}
      >
        <Ionicons name="add" size={28} color="#fff" />
      </TouchableOpacity>
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
  cardHeader: { marginBottom: 8 },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardTitle: { fontSize: 16, fontWeight: "600", color: colors.dark.textPrimary, flex: 1 },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  draftBadge: { backgroundColor: `${colors.brand.purple}30` },
  refinedBadge: { backgroundColor: `${colors.brand.cyan}30` },
  statusText: { fontSize: 11, fontWeight: "600", color: colors.dark.textSecondary },
  cardDesc: { fontSize: 14, color: colors.dark.textSecondary, marginBottom: 8 },
  refinedBox: {
    backgroundColor: `${colors.brand.cyan}10`,
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: colors.brand.cyan,
  },
  refinedLabel: { fontSize: 11, fontWeight: "600", color: colors.brand.cyan, marginBottom: 4 },
  refinedText: { fontSize: 13, color: colors.dark.textSecondary },
  cardFooter: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  dateText: { fontSize: 12, color: colors.dark.textMuted },
  refineBtn: { flexDirection: "row", alignItems: "center", gap: 4 },
  refineBtnText: { fontSize: 13, color: colors.brand.cyan, fontWeight: "500" },
  empty: { alignItems: "center", paddingTop: 100, gap: 8 },
  emptyText: { fontSize: 16, color: colors.dark.textSecondary },
  emptySubtext: { fontSize: 13, color: colors.dark.textMuted },
  fab: {
    position: "absolute",
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.brand.cyan,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.brand.cyan,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
});
