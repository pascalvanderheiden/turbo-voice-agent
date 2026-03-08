import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { colors } from "@/lib/theme";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.dark.bgSecondary },
          headerTintColor: colors.dark.textPrimary,
          headerTitleStyle: { fontWeight: "600" },
          contentStyle: { backgroundColor: colors.dark.bgPrimary },
          headerBackTitle: "Back",
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="note-form"
          options={{ presentation: "modal", title: "Note" }}
        />
        <Stack.Screen
          name="idea-form"
          options={{ presentation: "modal", title: "Idea" }}
        />
        <Stack.Screen
          name="research-list"
          options={{ title: "Research" }}
        />
        <Stack.Screen
          name="research-detail"
          options={{ title: "Research Detail" }}
        />
        <Stack.Screen
          name="specs-list"
          options={{ title: "Specs" }}
        />
        <Stack.Screen
          name="spec-detail"
          options={{ title: "Spec Detail" }}
        />
        <Stack.Screen
          name="agents"
          options={{ title: "Agents" }}
        />
        <Stack.Screen
          name="dev-list"
          options={{ title: "Development" }}
        />
        <Stack.Screen
          name="dev-detail"
          options={{ title: "Dev Task" }}
        />
      </Stack>
    </>
  );
}
