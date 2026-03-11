import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/lib/theme";
import { notesApi, ideasApi, researchApi, specsApi, type Note, type Idea, type Research, type Spec } from "@/lib/api";

interface DashboardCard {
  title: string;
  icon: keyof typeof Ionicons.glyphMap;
  count: number;
  color: string;
  onPress: () => void;
  subtitle?: string;
}

export default function DashboardScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState({ notes: 0, ideas: 0, research: 0, specs: 0 });

  const loadCounts = useCallback(async () => {
    setLoading(true);
    try {
      const [notes, ideas, research, specs] = await Promise.all([
        notesApi.list().catch(() => [] as Note[]),
        ideasApi.list().catch(() => [] as Idea[]),
        researchApi.list().catch(() => [] as Research[]),
        specsApi.list().catch(() => [] as Spec[]),
      ]);
      setCounts({
        notes: notes.length,
        ideas: ideas.length,
        research: research.length,
        specs: specs.length,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCounts(); }, [loadCounts]);

  const cards: DashboardCard[] = [
    {
      title: "Notes",
      icon: "document-text-outline",
      count: counts.notes,
      color: colors.brand.pink,
      onPress: () => router.push("/(tabs)/notes"),
      subtitle: "Quick notes & thoughts",
    },
    {
      title: "Ideas",
      icon: "bulb-outline",
      count: counts.ideas,
      color: colors.brand.cyan,
      onPress: () => router.push("/(tabs)/ideas"),
      subtitle: "Brainstorm & refine",
    },
    {
      title: "Research",
      icon: "search-outline",
      count: counts.research,
      color: colors.brand.purple,
      onPress: () => router.push("/research-list"),
      subtitle: "Web & deep research",
    },
    {
      title: "Specs",
      icon: "code-slash-outline",
      count: counts.specs,
      color: "#10B981",
      onPress: () => router.push("/specs-list"),
      subtitle: "Design specifications",
    },
    {
      title: "Agents",
      icon: "git-network-outline",
      count: 0,
      color: "#F59E0B",
      onPress: () => router.push("/agents"),
      subtitle: "Agent topology & status",
    },
    {
      title: "Voice",
      icon: "mic-outline",
      count: 0,
      color: colors.brand.pink,
      onPress: () => router.push("/(tabs)/voice"),
      subtitle: "Real-time voice agent",
    },
  ];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={loadCounts} tintColor={colors.brand.pink} />
      }
    >
      <Text style={styles.greeting}>Welcome back</Text>
      <Text style={styles.subtitle}>Turbo Voice Agent</Text>

      <View style={styles.grid}>
        {cards.map((card) => (
          <TouchableOpacity key={card.title} style={styles.card} onPress={card.onPress} activeOpacity={0.7}>
            <View style={[styles.iconCircle, { backgroundColor: `${card.color}20` }]}>
              <Ionicons name={card.icon} size={24} color={card.color} />
            </View>
            <Text style={styles.cardTitle}>{card.title}</Text>
            <Text style={styles.cardSubtitle}>{card.subtitle}</Text>
            {card.count != null && (
              <View style={[styles.badge, { backgroundColor: card.color }]}>
                <Text style={styles.badgeText}>{card.count}</Text>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  content: { padding: 16, paddingBottom: 32 },
  greeting: { fontSize: 28, fontWeight: "700", color: colors.dark.textPrimary, marginTop: 8 },
  subtitle: { fontSize: 14, color: colors.dark.textMuted, marginBottom: 24 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  card: {
    width: "48%",
    flexGrow: 1,
    backgroundColor: colors.dark.bgCard,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.dark.border,
    minHeight: 130,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  cardTitle: { fontSize: 16, fontWeight: "600", color: colors.dark.textPrimary, marginBottom: 2 },
  cardSubtitle: { fontSize: 12, color: colors.dark.textMuted },
  badge: {
    position: "absolute",
    top: 12,
    right: 12,
    minWidth: 24,
    height: 24,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  badgeText: { color: "#fff", fontSize: 12, fontWeight: "700" },
});
