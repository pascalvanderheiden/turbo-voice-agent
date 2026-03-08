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
import { specsApi, type Spec } from "@/lib/api";
import { colors } from "@/lib/theme";

export default function SpecsListScreen() {
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const s = await specsApi.list();
      setSpecs(s);
    } catch {
      Alert.alert("Error", "Failed to load specs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Group: foundations with their features
  const foundations = specs.filter((s) => s.type === "foundation");
  const featureMap = new Map<string, Spec[]>();
  for (const spec of specs) {
    if (spec.type === "feature" && spec.parentId) {
      if (!featureMap.has(spec.parentId)) featureMap.set(spec.parentId, []);
      featureMap.get(spec.parentId)!.push(spec);
    }
  }

  const handleDelete = (spec: Spec) => {
    const isFoundation = spec.type === "foundation";
    const featureCount = featureMap.get(spec.id)?.length || 0;
    const msg = isFoundation && featureCount > 0
      ? `Delete "${spec.title}" and its ${featureCount} feature(s)?`
      : `Delete "${spec.title}"?`;

    Alert.alert("Delete Spec", msg, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => { await specsApi.delete(spec.id); load(); },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={foundations}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} tintColor="#10B981" />}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Ionicons name="code-slash-outline" size={48} color={colors.dark.textMuted} />
              <Text style={styles.emptyText}>No specs yet</Text>
              <Text style={styles.emptySubtext}>Generate specs from ideas</Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => {
          const features = featureMap.get(item.id) || [];
          return (
            <TouchableOpacity
              style={styles.card}
              onPress={() => router.push({ pathname: "/spec-detail", params: { id: item.id } })}
              onLongPress={() => handleDelete(item)}
            >
              {/* Foundation header */}
              <View style={styles.cardHeader}>
                <View style={styles.foundBadge}>
                  <Text style={styles.foundBadgeText}>Foundation</Text>
                </View>
                <View style={[styles.statusDot, { backgroundColor: item.status === "optimized" ? "#10B981" : colors.dark.textMuted }]} />
              </View>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardContent} numberOfLines={3}>{item.content}</Text>

              {/* Feature pills */}
              {features.length > 0 && (
                <View style={styles.featureRow}>
                  {features.map((f) => (
                    <TouchableOpacity
                      key={f.id}
                      style={styles.featurePill}
                      onPress={() => router.push({ pathname: "/spec-detail", params: { id: f.id } })}
                    >
                      <Ionicons name="layers-outline" size={12} color={colors.brand.cyan} />
                      <Text style={styles.featurePillText} numberOfLines={1}>{f.title}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}

              <Text style={styles.dateText}>{new Date(item.updatedAt).toLocaleDateString()}</Text>
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  list: { padding: 16, paddingBottom: 32 },
  card: {
    padding: 14,
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.dark.border,
    marginBottom: 12,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  foundBadge: { backgroundColor: `${colors.brand.purple}20`, paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  foundBadgeText: { fontSize: 11, fontWeight: "600", color: colors.brand.purple },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  cardTitle: { fontSize: 16, fontWeight: "600", color: colors.dark.textPrimary, marginBottom: 4 },
  cardContent: { fontSize: 13, color: colors.dark.textSecondary, marginBottom: 10 },
  featureRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 10 },
  featurePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: `${colors.brand.cyan}12`,
    borderWidth: 1,
    borderColor: `${colors.brand.cyan}30`,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  featurePillText: { fontSize: 12, color: colors.brand.cyan, maxWidth: 160 },
  dateText: { fontSize: 12, color: colors.dark.textMuted },
  empty: { alignItems: "center", paddingTop: 100, gap: 8 },
  emptyText: { fontSize: 16, color: colors.dark.textSecondary },
  emptySubtext: { fontSize: 13, color: colors.dark.textMuted },
});
