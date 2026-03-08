import { useCallback, useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { specsApi, devApi, type Spec } from "@/lib/api";
import { colors } from "@/lib/theme";

export default function SpecDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [spec, setSpec] = useState<Spec | null>(null);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [developing, setDeveloping] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setSpec(await specsApi.get(id));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleOptimize = async () => {
    if (!spec) return;
    setOptimizing(true);
    try {
      await specsApi.optimize(spec.id);
      await load();
      Alert.alert("Optimized", "Spec has been optimized by AI");
    } catch {
      Alert.alert("Error", "Failed to optimize spec");
    } finally {
      setOptimizing(false);
    }
  };

  const handleDevelop = async () => {
    if (!spec) return;
    setDeveloping(true);
    try {
      const task = await devApi.create({ title: spec.title, specId: spec.id });
      Alert.alert("Dev Task Created", "Navigate to the dev task?", [
        { text: "Later", style: "cancel" },
        { text: "Go", onPress: () => router.push(`/dev-detail?id=${task.id}`) },
      ]);
    } catch {
      Alert.alert("Error", "Failed to create dev task");
    } finally {
      setDeveloping(false);
    }
  };

  if (loading || !spec) {
    return (
      <View style={styles.center}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>{spec.title}</Text>
        <View style={styles.meta}>
          <View style={[styles.badge, spec.type === "foundation" ? styles.foundBadge : styles.featBadge]}>
            <Text style={[styles.badgeText, { color: spec.type === "foundation" ? colors.brand.purple : colors.brand.cyan }]}>
              {spec.type}
            </Text>
          </View>
          <View style={[styles.badge, { backgroundColor: spec.status === "optimized" ? "#10B98120" : `${colors.dark.textMuted}20` }]}>
            <Text style={[styles.badgeText, { color: spec.status === "optimized" ? "#10B981" : colors.dark.textMuted }]}>
              {spec.status}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Content</Text>
        <Text style={styles.contentText}>{spec.content}</Text>
      </View>

      {spec.status !== "optimized" && (
        <TouchableOpacity
          style={[styles.optimizeBtn, optimizing && styles.disabled]}
          onPress={handleOptimize}
          disabled={optimizing}
        >
          <Ionicons name="sparkles-outline" size={18} color="#fff" />
          <Text style={styles.optimizeBtnText}>
            {optimizing ? "Optimizing..." : "Optimize with AI"}
          </Text>
        </TouchableOpacity>
      )}

      {spec.type === "foundation" && (
        <TouchableOpacity
          style={[styles.developBtn, developing && styles.disabled]}
          onPress={handleDevelop}
          disabled={developing}
        >
          <Ionicons name="code-slash-outline" size={18} color="#fff" />
          <Text style={styles.optimizeBtnText}>
            {developing ? "Creating..." : "Develop"}
          </Text>
        </TouchableOpacity>
      )}

      <Text style={styles.dateFooter}>
        Updated {new Date(spec.updatedAt).toLocaleString()}
      </Text>
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
  foundBadge: { backgroundColor: `${colors.brand.purple}20` },
  featBadge: { backgroundColor: `${colors.brand.cyan}15` },
  badgeText: { fontSize: 12, fontWeight: "600" },
  section: { marginBottom: 20 },
  sectionLabel: { fontSize: 13, fontWeight: "600", color: colors.dark.textMuted, marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 },
  contentText: { fontSize: 15, color: colors.dark.textPrimary, lineHeight: 24 },
  optimizeBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#10B981",
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
  },
  developBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.brand.pink,
    borderRadius: 10,
    padding: 14,
    marginBottom: 20,
  },
  disabled: { opacity: 0.5 },
  optimizeBtnText: { color: "#fff", fontSize: 15, fontWeight: "600" },
  dateFooter: { fontSize: 12, color: colors.dark.textMuted, textAlign: "center" },
});
