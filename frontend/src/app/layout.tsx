import type { Metadata } from "next";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";
import { I18nProvider } from "@/lib/i18n";
import { NotificationProvider } from "@/lib/notifications";
import { VoiceProvider } from "@/lib/voice-provider";
import { VoiceOverlay } from "@/components/voice/voice-overlay";
import { AuthProvider } from "@/lib/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Turbo Voice Agent",
  description: "Real-time conversational AI voice agent",
  icons: { icon: "/favicon.png", apple: "/apple-touch-icon.png" },
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Turbo Agent",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <AuthProvider>
        <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem={false}>
          <I18nProvider>
            <NotificationProvider>
              <VoiceProvider>
                <div className="flex h-screen overflow-hidden">
                  {children}
                </div>
                <VoiceOverlay />
              </VoiceProvider>
              <Toaster
                theme="dark"
                position="bottom-right"
                toastOptions={{
                  style: {
                    background: "var(--color-bg-card)",
                    border: "1px solid var(--color-border-dark)",
                    color: "var(--color-text-primary)",
                  },
                }}
              />
            </NotificationProvider>
          </I18nProvider>
        </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
