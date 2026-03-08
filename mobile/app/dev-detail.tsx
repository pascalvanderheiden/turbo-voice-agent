import { View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity, Image } from "react-native";
import { useEffect, useState, useCallback, useRef } from "react";
import { useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/lib/theme";
import { devApi, type DevTask, type DevIteration } from "@/lib/api";

const STAGE_META: Record<string, { iconName: keyof typeof Ionicons.glyphMap; label: string; color: string }> = {
  plan: { iconName: "clipboard-outline", label: "Plan", color: colors.brand.purple },
  build: { iconName: "hammer-outline", label: "Build", color: colors.brand.cyan },
  run: { iconName: "rocket-outline", label: "Run", color: colors.brand.pink },
  test: { iconName: "flask-outline", label: "Test", color: "#22C55E" },
};

const STATUS_COLORS: Record<string, string> = {
  pending: "#666",
  running: "#3B82F6",
  completed: "#22C55E",
  failed: "#EF4444",
};

function PlanOutput({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <View style={styles.planContainer}>
      {lines.map((line, i) => {
        const trimmed = line.trimStart();
        if (trimmed.startsWith("# ")) {
          return <Text key={i} style={styles.planH1}>{trimmed.slice(2)}</Text>;
        }
        if (trimmed.startsWith("## ")) {
          return <Text key={i} style={styles.planH2}>{trimmed.slice(3)}</Text>;
        }
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <View key={i} style={styles.planBulletRow}>
              <Text style={styles.planBullet}>•</Text>
              <Text style={styles.planBulletText}>{trimmed.slice(2)}</Text>
            </View>
          );
        }
        if (/^\d+\.\s/.test(trimmed)) {
          const numEnd = trimmed.indexOf(". ");
          return (
            <View key={i} style={styles.planBulletRow}>
              <Text style={styles.planNumber}>{trimmed.slice(0, numEnd + 1)}</Text>
              <Text style={styles.planBulletText}>{trimmed.slice(numEnd + 2)}</Text>
            </View>
          );
        }
        if (trimmed === "") {
          return <View key={i} style={{ height: 6 }} />;
        }
        return <Text key={i} style={styles.planText}>{line}</Text>;
      })}
    </View>
  );
}

function StagesList({ stages }: { stages: DevIteration["stages"] }) {
  return (
    <>
      {stages.map((stage, i) => {
        const meta = STAGE_META[stage.name] || { iconName: "help-outline" as keyof typeof Ionicons.glyphMap, label: stage.name, color: "#666" };
        return (
          <View key={stage.name} style={styles.stageRow}>
            <View style={styles.stageLeft}>
              <View style={[styles.stageCircle, { borderColor: STATUS_COLORS[stage.status] || "#666" }]}>
                {stage.status === "completed" ? (
                  <Ionicons name="checkmark" size={16} color="#22C55E" />
                ) : stage.status === "running" ? (
                  <ActivityIndicator size={14} color="#3B82F6" />
                ) : stage.status === "failed" ? (
                  <Ionicons name="close" size={16} color="#EF4444" />
                ) : (
                  <Ionicons name={meta.iconName} size={16} color={meta.color} />
                )}
              </View>
              {i < stages.length - 1 && <View style={styles.stageLine} />}
            </View>
            <View style={styles.stageInfo}>
              <View style={styles.stageHeader}>
                <Text style={styles.stageLabel}>{meta.label}</Text>
                <View style={[styles.statusDot, { backgroundColor: STATUS_COLORS[stage.status] }]} />
              </View>
              {stage.output && stage.name === "plan" ? (
                <PlanOutput text={stage.output} />
              ) : stage.output ? (
                <Text style={styles.stageOutput} numberOfLines={8}>{stage.output}</Text>
              ) : null}
              {stage.error && (
                <Text style={styles.stageError} numberOfLines={4}>{stage.error}</Text>
              )}
            </View>
          </View>
        );
      })}
    </>
  );
}

export default function DevDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [task, setTask] = useState<DevTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeIter, setActiveIter] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await devApi.get(id);
      setTask(data);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const isRunning = task?.status === "running";
  useEffect(() => {
    if (!isRunning) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try { setTask(await devApi.get(id)); } catch {}
    }, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [isRunning, id]);

  const handleTrigger = async () => {
    if (!task) return;
    try {
      await devApi.trigger(task.id);
      load();
    } catch {}
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brand.pink} />
      </View>
    );
  }

  if (!task) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>Task not found</Text>
      </View>
    );
  }

  const screenshots = task.artifacts.filter((a) => a.type === "screenshot" && a.name.endsWith(".png"));
  const iterations: DevIteration[] = task.iterations && task.iterations.length > 0
    ? task.iterations
    : [{ iterationIndex: 0, label: task.title, stages: task.stages }];
  const isSequence = task.mode === "sequence" && iterations.length > 1;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <Text style={styles.title}>{task.title}</Text>
      <View style={{ flexDirection: "row", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
        {task.mode && (
          <View style={[styles.badge, { backgroundColor: task.mode === "sequence" ? `${colors.brand.purple}20` : `${colors.brand.cyan}20` }]}>
            <Text style={[styles.badgeText, { color: task.mode === "sequence" ? colors.brand.purple : colors.brand.cyan }]}>
              {task.mode === "sequence" ? "Sequence" : "Mock"}
            </Text>
          </View>
        )}
        <View style={[styles.badge, { backgroundColor: `${STATUS_COLORS[task.status] || "#666"}20` }]}>
          <Text style={[styles.badgeText, { color: STATUS_COLORS[task.status] || "#666" }]}>
            {task.status}
          </Text>
        </View>
        {task.skillIds && task.skillIds.length > 0 && task.skillIds.map((s) => (
          <View key={s} style={[styles.badge, { backgroundColor: `${colors.brand.pink}20` }]}>
            <Text style={[styles.badgeText, { color: colors.brand.pink }]}>{s}</Text>
          </View>
        ))}
      </View>

      {(task.status === "pending" || task.status === "failed") && (
        <TouchableOpacity style={styles.triggerBtn} onPress={handleTrigger} activeOpacity={0.8}>
          <Ionicons name="play" size={16} color="#fff" />
          <Text style={styles.triggerText}>Run Pipeline</Text>
        </TouchableOpacity>
      )}

      {/* Iteration tabs for sequence mode */}
      {isSequence && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
          {iterations.map((it, i) => {
            const allDone = it.stages.every((s) => s.status === "completed");
            const anyFailed = it.stages.some((s) => s.status === "failed");
            const isActive = activeIter === i;
            return (
              <TouchableOpacity
                key={i}
                onPress={() => setActiveIter(i)}
                style={[
                  styles.iterTab,
                  isActive ? { borderColor: colors.brand.pink, backgroundColor: `${colors.brand.pink}15` }
                  : allDone ? { borderColor: "#22C55E40", backgroundColor: "#22C55E08" }
                  : anyFailed ? { borderColor: "#EF444440", backgroundColor: "#EF444408" }
                  : { borderColor: colors.dark.border },
                ]}
              >
                <Text style={[styles.iterTabText, isActive ? { color: colors.brand.pink } : allDone ? { color: "#22C55E" } : anyFailed ? { color: "#EF4444" } : {}]}>
                  {it.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}

      {/* Active iteration stages */}
      <Text style={styles.sectionTitle}>
        {isSequence ? iterations[activeIter]?.label || "Stages" : "Pipeline Stages"}
      </Text>
      <StagesList stages={iterations[activeIter]?.stages || task.stages} />

      {/* Screenshots */}
      {screenshots.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Screenshots</Text>
          {screenshots.map((a, i) => (
            <View key={i} style={styles.screenshotCard}>
              <Image
                source={{ uri: `data:image/png;base64,${a.data}` }}
                style={styles.screenshot}
                resizeMode="contain"
              />
              <Text style={styles.screenshotName}>{a.name}</Text>
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: colors.dark.bgPrimary },
  emptyText: { color: colors.dark.textMuted, fontSize: 14 },
  title: { fontSize: 20, fontWeight: "700", color: colors.dark.textPrimary, marginBottom: 8 },
  badge: { alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10 },
  badgeText: { fontSize: 12, fontWeight: "600" },
  triggerBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.brand.pink,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    alignSelf: "flex-start",
    marginBottom: 20,
  },
  triggerText: { color: "#fff", fontWeight: "600", fontSize: 14 },
  sectionTitle: { fontSize: 13, fontWeight: "600", color: colors.dark.textMuted, marginBottom: 12, marginTop: 8 },
  stageRow: { flexDirection: "row", marginBottom: 8 },
  stageLeft: { width: 44, alignItems: "center" },
  stageCircle: { width: 36, height: 36, borderRadius: 18, borderWidth: 2, justifyContent: "center", alignItems: "center", backgroundColor: colors.dark.bgCard },
  stageLine: { width: 2, flex: 1, backgroundColor: colors.dark.border, marginVertical: 2 },
  stageInfo: { flex: 1, paddingLeft: 12, paddingBottom: 12 },
  stageHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  stageLabel: { fontSize: 15, fontWeight: "600", color: colors.dark.textPrimary },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  stageOutput: { fontSize: 12, color: colors.dark.textSecondary, marginTop: 6, backgroundColor: colors.dark.bgTertiary, padding: 8, borderRadius: 6 },
  stageError: { fontSize: 12, color: "#EF4444", marginTop: 6, backgroundColor: "#EF444410", padding: 8, borderRadius: 6 },
  planContainer: { marginTop: 6, backgroundColor: colors.dark.bgTertiary, padding: 10, borderRadius: 6 },
  planH1: { fontSize: 14, fontWeight: "700", color: colors.brand.purple, marginBottom: 4 },
  planH2: { fontSize: 13, fontWeight: "600", color: colors.brand.cyan, marginBottom: 3, marginTop: 4 },
  planBulletRow: { flexDirection: "row", paddingLeft: 4, marginBottom: 2 },
  planBullet: { fontSize: 12, color: colors.brand.pink, width: 14, lineHeight: 18 },
  planNumber: { fontSize: 12, color: colors.brand.cyan, width: 20, lineHeight: 18, fontWeight: "600" },
  planBulletText: { flex: 1, fontSize: 12, color: colors.dark.textPrimary, lineHeight: 18 },
  planText: { fontSize: 12, color: colors.dark.textSecondary, lineHeight: 18 },
  screenshotCard: { backgroundColor: colors.dark.bgCard, borderRadius: 8, overflow: "hidden", borderWidth: 1, borderColor: colors.dark.border, marginBottom: 12 },
  screenshot: { width: "100%", height: 200 },
  screenshotName: { padding: 8, fontSize: 11, color: colors.dark.textMuted },
  iterTab: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, borderWidth: 1, marginRight: 6 },
  iterTabText: { fontSize: 12, fontWeight: "600", color: colors.dark.textMuted },
});
