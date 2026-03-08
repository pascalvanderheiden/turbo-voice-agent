import { Tabs } from "expo-router";
import { Image, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "@/lib/theme";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          backgroundColor: colors.dark.bgSecondary,
          borderTopColor: colors.dark.border,
          height: 85,
          paddingBottom: 28,
        },
        tabBarActiveTintColor: colors.brand.pink,
        tabBarInactiveTintColor: colors.dark.textMuted,
        headerStyle: { backgroundColor: colors.dark.bgSecondary },
        headerTintColor: colors.dark.textPrimary,
        headerLeft: () => (
          <Image
            source={require("../../assets/logo.png")}
            style={{ width: 28, height: 28, marginLeft: 16 }}
            resizeMode="contain"
          />
        ),
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="grid-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="notes"
        options={{
          title: "Notes",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="document-text-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="voice"
        options={{
          title: "Turbo",
          tabBarIcon: ({ focused }) => (
            <View style={[voiceStyles.voiceTab, focused && voiceStyles.voiceTabActive]}>
              <Ionicons name={focused ? "chatbubbles" : "chatbubbles-outline"} size={26} color="#fff" />
            </View>
          ),
          tabBarLabel: () => null,
        }}
      />
      <Tabs.Screen
        name="ideas"
        options={{
          title: "Ideas",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="bulb-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="more"
        options={{
          title: "More",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="ellipsis-horizontal" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}

const voiceStyles = StyleSheet.create({
  voiceTab: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.brand.pink,
    alignItems: "center",
    justifyContent: "center",
    marginTop: -16,
    shadowColor: colors.brand.pink,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 8,
  },
  voiceTabActive: {
    backgroundColor: colors.brand.purple,
  },
});
