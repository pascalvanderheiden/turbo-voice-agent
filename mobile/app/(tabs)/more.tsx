import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/lib/theme";

interface MenuItem {
  title: string;
  subtitle: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
  route: string;
}

const menuItems: MenuItem[] = [
  {
    title: "Research",
    subtitle: "Web search & deep research",
    icon: "search-outline",
    color: colors.brand.purple,
    route: "/research-list",
  },
  {
    title: "Specs",
    subtitle: "Design specifications",
    icon: "code-slash-outline",
    color: "#10B981",
    route: "/specs-list",
  },
  {
    title: "Development",
    subtitle: "Build apps from specs",
    icon: "hammer-outline",
    color: colors.brand.pink,
    route: "/dev-list",
  },
  {
    title: "Agents",
    subtitle: "Agent topology & status",
    icon: "git-network-outline",
    color: "#F59E0B",
    route: "/agents",
  },
];

export default function MoreScreen() {
  const router = useRouter();

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {menuItems.map((item) => (
        <TouchableOpacity
          key={item.title}
          style={styles.menuItem}
          onPress={() => router.push(item.route as any)}
          activeOpacity={0.7}
        >
          <View style={[styles.iconCircle, { backgroundColor: `${item.color}20` }]}>
            <Ionicons name={item.icon} size={22} color={item.color} />
          </View>
          <View style={styles.menuText}>
            <Text style={styles.menuTitle}>{item.title}</Text>
            <Text style={styles.menuSubtitle}>{item.subtitle}</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.dark.textMuted} />
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  content: { padding: 16, gap: 8 },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.dark.border,
    gap: 14,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  menuText: { flex: 1 },
  menuTitle: { fontSize: 16, fontWeight: "600", color: colors.dark.textPrimary },
  menuSubtitle: { fontSize: 13, color: colors.dark.textMuted, marginTop: 2 },
});
