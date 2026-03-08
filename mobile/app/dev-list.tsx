import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/lib/theme";
import { devApi, type DevTask } from "@/lib/api";

const STAGE_ICONS: Record<string, { name: keyof typeof Ionicons.glyphMap; color: string }> = {
  plan: { name: "clipboard-outline", color: colors.brand.purple },
  build: { name: "hammer-outline", color: colors.brand.cyan },
  run: { name: "rocket-outline", color: colors.brand.pink },
  test: { name: "flask-outline", color: "#22C55E" },
};
const STATUS_COLORS: Record<string, string> = {
  pending: "#EAB308",
  running: "#3B82F6",
  completed: "#22C55E",
  failed: "#EF4444",
};

export default function DevListScreen() {
  const [tasks, setTasks] = useState<DevTask[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await devApi.list();
      setTasks(data);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const hasRunning = tasks.some((t) => t.status === "running");
  useEffect(() => {
    if (!hasRunning) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try { setTasks(await devApi.list()); } catch {}
    }, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [hasRunning]);

  const c = colors.dark;

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: c.bgPrimary }]}>
        <ActivityIndicator color={colors.brand.pink} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={tasks}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="hammer-outline" size={48} color={c.textMuted} />
            <Text style={styles.emptyText}>No development tasks yet</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => router.push({ pathname: "/dev-detail", params: { id: item.id } } as any)}
            activeOpacity={0.7}
          >
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle} numberOfLines={1}>{item.title}</Text>
              <View style={{ flexDirection: "row", gap: 4, alignItems: "center" }}>
                {item.mode && (
                  <View style={[styles.badge, { backgroundColor: item.mode === "sequence" ? `${colors.brand.purple}20` : `${colors.brand.cyan}20` }]}>
                    <Text style={[styles.badgeText, { color: item.mode === "sequence" ? colors.brand.purple : colors.brand.cyan }]}>
                      {item.mode === "sequence" ? "Sequence" : "Mock"}
                    </Text>
                  </View>
                )}
                <View style={[styles.badge, { backgroundColor: `${STATUS_COLORS[item.status] || "#666"}20` }]}>
                  <Text style={[styles.badgeText, { color: STATUS_COLORS[item.status] || "#666" }]}>
                    {item.status}
                  </Text>
                </View>
              </View>
            </View>
            <View style={styles.pipeline}>
              {item.stages.map((stage, i) => (
                <View key={stage.name} style={styles.pipelineStep}>
                  <View style={[
                    styles.stageCircle,
                    {
                      backgroundColor: stage.status === "completed" ? "#22C55E"
                        : stage.status === "running" ? "#3B82F6"
                        : stage.status === "failed" ? "#EF4444"
                        : c.bgTertiary,
                    },
                  ]}>
                    {stage.status === "completed" ? (
                      <Ionicons name="checkmark" size={14} color="#fff" />
                    ) : stage.status === "running" ? (
                      <ActivityIndicator size={12} color="#fff" />
                    ) : stage.status === "failed" ? (
                      <Ionicons name="close" size={14} color="#fff" />
                    ) : (
                      <Ionicons
                        name={STAGE_ICONS[stage.name]?.name || "help-outline"}
                        size={14}
                        color={STAGE_ICONS[stage.name]?.color || c.textMuted}
                      />
                    )}
                  </View>
                  {i < item.stages.length - 1 && (
                    <View style={[
                      styles.connector,
                      { backgroundColor: stage.status === "completed" ? "#22C55E50" : c.border },
                    ]} />
                  )}
                </View>
              ))}
            </View>
            <Text style={styles.date}>
              {new Date(item.createdAt).toLocaleDateString()}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  list: { padding: 16, gap: 12 },
  empty: { alignItems: "center", paddingTop: 60, gap: 12 },
  emptyText: { color: colors.dark.textMuted, fontSize: 14 },
  card: {
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.dark.border,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  cardTitle: { fontSize: 15, fontWeight: "600", color: colors.dark.textPrimary, flex: 1, marginRight: 8 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  badgeText: { fontSize: 11, fontWeight: "600" },
  pipeline: { flexDirection: "row", alignItems: "center", gap: 0 },
  pipelineStep: { flexDirection: "row", alignItems: "center" },
  stageCircle: { width: 32, height: 32, borderRadius: 16, justifyContent: "center", alignItems: "center" },
  connector: { width: 16, height: 2 },
  date: { color: colors.dark.textMuted, fontSize: 11, marginTop: 10 },
});
