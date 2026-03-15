"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconMicrophone, IconBell } from "@tabler/icons-react";
import { UserMenu } from "./user-menu";
import { useI18n } from "@/lib/i18n";
import { useNotifications } from "@/lib/notifications";

export function SiteHeader() {
  const pathname = usePathname();
  const { locale, t } = useI18n();
  const { notifications, unreadCount, markAllRead, clearAll } = useNotifications();
  const [showNotifications, setShowNotifications] = useState(false);
  const [userInfo, setUserInfo] = useState<{ name: string; email: string } | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID;
    if (!clientId) {
      // Local dev fallback — show user menu without MSAL
      setUserInfo({ name: "Local User", email: "dev@localhost" });
      return;
    }
    import("@/lib/msal-config").then(({ getMsalInstance }) => {
      const instance = getMsalInstance();
      const accounts = instance.getAllAccounts();
      if (accounts.length > 0) {
        setUserInfo({
          name: accounts[0].name || "",
          email: accounts[0].username || "",
        });
        // Fetch profile photo as blob via authenticated API proxy
        import("@/lib/api").then(({ userApi }) => {
          userApi.getPhotoObjectUrl().then((url) => {
            if (url) setPhotoUrl(url);
          }).catch(() => { /* photo not available */ });
        });
      }
    });
  }, []);

  // Close panel on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    if (showNotifications) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showNotifications]);

  const breadcrumb = pathname
    .split("/")
    .filter(Boolean)
    .map((seg) => seg.charAt(0).toUpperCase() + seg.slice(1));

  const toggleNotifications = () => {
    setShowNotifications(!showNotifications);
    if (!showNotifications && unreadCount > 0) {
      markAllRead();
    }
  };

  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-[var(--color-border-dark)] bg-[var(--color-bg-secondary)]">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-[var(--color-text-muted)]">{t("header.brand")}</span>
        {breadcrumb.map((crumb, i) => (
          <span key={i} className="flex items-center gap-2">
            <span className="text-[var(--color-text-muted)]">/</span>
            <span className="text-[var(--color-text-primary)]">{crumb}</span>
          </span>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* User menu */}
        {userInfo && (
          <UserMenu displayName={userInfo.name} email={userInfo.email} photoUrl={photoUrl} onPhotoChange={setPhotoUrl} />
        )}

        {/* Notification bell */}
        <div className="relative" ref={panelRef}>
          <button
            onClick={toggleNotifications}
            className="relative flex items-center justify-center w-9 h-9 rounded-full text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
            title="Notifications"
          >
            <IconBell size={18} stroke={1.5} />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center w-4 h-4 text-[10px] font-bold text-white rounded-full bg-[var(--color-brand-pink)]">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Notification panel */}
          {showNotifications && (
            <div className="absolute right-0 top-11 w-80 max-h-96 rounded-2xl border border-[var(--color-border-dark)] bg-[var(--color-bg-card)] shadow-xl overflow-hidden z-50" style={{ backdropFilter: "blur(20px)" }}>
              <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-dark)]">
                <span className="text-[13px] font-semibold text-[var(--color-text-primary)]">
                  {locale === "nl" ? "Activiteit" : "Activity"}
                </span>
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="text-[12px] text-[var(--color-brand-pink)] hover:opacity-70 transition-opacity"
                  >
                    {locale === "nl" ? "Wis alles" : "Clear all"}
                  </button>
                )}
              </div>
              <div className="overflow-y-auto max-h-72">
                {notifications.length === 0 ? (
                  <div className="px-4 py-10 text-center text-[13px] text-[var(--color-text-muted)]">
                    {locale === "nl" ? "Geen activiteit" : "No activity yet"}
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border-dark)]/50 last:border-b-0"
                    >
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${!n.read ? "bg-[var(--color-brand-pink)]" : "bg-[var(--color-text-muted)]/30"}`} />
                      <span className="text-[13px] text-[var(--color-text-primary)] truncate">{n.title}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <Link
          href="/voice"
          className="flex items-center justify-center w-9 h-9 rounded-full bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)] hover:bg-[var(--color-brand-pink)]/20 transition-colors"
          title={t("nav.voice")}
        >
          <IconMicrophone size={18} stroke={1.5} />
        </Link>
      </div>
    </header>
  );
}
