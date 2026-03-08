/* Turbo Agent brand colors and theme */

export const colors = {
  brand: {
    pink: "#E91E8C",
    cyan: "#00D4FF",
    purple: "#7B2FBE",
  },
  dark: {
    bgPrimary: "#0F0F1A",
    bgSecondary: "#1A1A2E",
    bgTertiary: "#252540",
    bgCard: "#1E1E32",
    textPrimary: "#FFFFFF",
    textSecondary: "#A0A0B8",
    textMuted: "#6B6B80",
    border: "#2A2A42",
  },
  light: {
    bgPrimary: "#FAFAFA",
    bgSecondary: "#FFFFFF",
    bgTertiary: "#F0F0F5",
    bgCard: "#FFFFFF",
    textPrimary: "#0F0F1A",
    textSecondary: "#4A4A5C",
    textMuted: "#8B8B9E",
    border: "#E2E2EA",
  },
} as const;

export type ThemeMode = "dark" | "light";

export function getThemeColors(mode: ThemeMode = "dark") {
  return mode === "dark" ? colors.dark : colors.light;
}
