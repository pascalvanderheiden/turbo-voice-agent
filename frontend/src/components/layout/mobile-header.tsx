"use client";

import { useEffect, useState, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { IconSettings, IconBell, IconServer } from "@tabler/icons-react";
import { useI18n } from "@/lib/i18n";
import { useNotifications } from "@/lib/notifications";
import { sandboxApi } from "@/lib/sandbox-api";

const SANDBOX_STATUS_STYLES: Record<string, { dot: string; pulse?: boolean }> = {
  ready:          { dot: "bg-green-400" },
  busy:           { dot: "bg-yellow-400", pulse: true },
  provisioning:   { dot: "bg-yellow-400", pulse: true },
  stopped:        { dot: "bg-[var(--color-text-muted)]" },
  error:          { dot: "bg-red-400" },
  not_configured: { dot: "bg-[var(--color-text-muted)]" },
  loading:        { dot: "bg-[var(--color-text-muted)]" },
};

export function MobileHeader() {
  const { locale, t } = useI18n();
  const { notifications, unreadCount, markAllRead, clearAll } = useNotifications();
  const [showNotifications, setShowNotifications] = useState(false);
  const [sandboxStatus, setSandboxStatus] = useState<{
    status: string;
    activeTasks: number;
  }>({ status: "loading", activeTasks: 0 });
  const panelRef = useRef<HTMLDivElement>(null);

  // Close notification panel on outside click
  useEffect(() => {
    if (!showNotifications) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showNotifications]);

  // Poll sandbox status
  useEffect(() => {
    let mounted = true;
    const fetchStatus = () => {
      sandboxApi
        .status()
        .then((data) => { if (mounted) setSandboxStatus(data); })
        .catch(() => { if (mounted) setSandboxStatus({ status: "error", activeTasks: 0 }); });
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10_000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const toggleNotifications = () => {
    setShowNotifications(!showNotifications);
    if (!showNotifications && unreadCount > 0) markAllRead();
  };

  const sbStyle = SANDBOX_STATUS_STYLES[sandboxStatus.status]
    ?? SANDBOX_STATUS_STYLES.loading;

  return (
    <header className="flex items-center justify-between h-12 px-4 border-b border-[var(--color-border-dark)] bg-[var(--color-bg-secondary)] flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <Image src="/logo.png" alt="Turbo Agent" width={28} height={28} />
        <span className="font-semibold text-sm gradient-brand-text">
          Turbo Agent
        </span>
      </div>

      {/* Right actions: sandbox, notifications, settings */}
      <div className="flex items-center gap-1">
        {/* Sandbox indicator */}
        <Link
          href="/agents"
          className="relative flex items-center justify-center w-9 h-9 rounded-full text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          title={`Sandbox: ${sandboxStatus.status}`}
        >
          <IconServer size={18} stroke={1.5} />
          <span
            className={`absolute top-1 right-1 w-2 h-2 rounded-full border-[1.5px] border-[var(--color-bg-secondary)] ${sbStyle.dot}${sbStyle.pulse ? " animate-pulse" : ""}`}
          />
          {sandboxStatus.activeTasks > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center w-3.5 h-3.5 text-[9px] font-bold text-white rounded-full bg-[var(--color-brand-pink)]">
              {sandboxStatus.activeTasks > 9 ? "9+" : sandboxStatus.activeTasks}
            </span>
          )}
        </Link>

        {/* Notification bell */}
        <div className="relative" ref={panelRef}>
          <button
            onClick={toggleNotifications}
            className="relative flex items-center justify-center w-9 h-9 rounded-full text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
            title="Notifications"
          >
            <IconBell size={18} stroke={1.5} />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center w-3.5 h-3.5 text-[9px] font-bold text-white rounded-full bg-[var(--color-brand-pink)]">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Notification dropdown */}
          {showNotifications && (
            <div className="absolute right-0 top-11 w-72 max-h-80 rounded-2xl border border-[var(--color-border-dark)] bg-[var(--color-bg-card)] shadow-xl overflow-hidden z-50">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--color-border-dark)]">
                <span className="text-[13px] font-semibold">
                  {locale === "nl" ? "Activiteit" : "Activity"}
                </span>
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="text-[11px] text-[var(--color-brand-pink)] hover:opacity-70 transition-opacity"
                  >
                    {locale === "nl" ? "Wis alles" : "Clear all"}
                  </button>
                )}
              </div>
              <div className="overflow-y-auto max-h-64">
                {notifications.length === 0 ? (
                  <div className="px-4 py-8 text-center text-[13px] text-[var(--color-text-muted)]">
                    {locale === "nl" ? "Geen activiteit" : "No activity yet"}
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className="flex items-center gap-3 px-4 py-2.5 border-b border-[var(--color-border-dark)]/50 last:border-b-0"
                    >
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${!n.read ? "bg-[var(--color-brand-pink)]" : "bg-[var(--color-text-muted)]/30"}`} />
                      <span className="text-[12px] text-[var(--color-text-primary)] truncate">
                        {n.title}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Settings — direct link to settings page */}
        <Link
          href="/settings"
          className="flex items-center justify-center w-9 h-9 rounded-full text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          title={t("nav.settings") || "Settings"}
        >
          <IconSettings size={18} stroke={1.5} />
        </Link>
      </div>
    </header>
  );
}
