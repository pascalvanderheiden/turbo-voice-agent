"use client";

import { useEffect, useState, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  IconSettings,
  IconX,
  IconLayoutDashboard,
  IconCode,
  IconVideo,
  IconBolt,
  IconMessageCircle,
  IconPlugConnected,
} from "@tabler/icons-react";
import { useI18n } from "@/lib/i18n";
import { useNotifications } from "@/lib/notifications";

const secondaryNav = [
  { href: "/dashboard", labelKey: "nav.dashboard", icon: IconLayoutDashboard },
  { href: "/development", labelKey: "nav.development", icon: IconCode },
  { href: "/marketing", labelKey: "nav.marketing", icon: IconVideo },
  { href: "/agents", labelKey: "nav.agents", icon: IconBolt },
  { href: "/chat", labelKey: "nav.chat", icon: IconMessageCircle },
  { href: "/settings", labelKey: "nav.settings", icon: IconPlugConnected },
];

export function MobileHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { t } = useI18n();
  const { unreadCount } = useNotifications();
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  return (
    <>
      <header className="flex items-center justify-between h-12 px-4 border-b border-[var(--color-border-dark)] bg-[var(--color-bg-secondary)] flex-shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Image src="/logo.png" alt="Turbo Agent" width={28} height={28} />
          <span className="font-semibold text-sm gradient-brand-text">Turbo Agent</span>
        </div>

        {/* Settings gear with notification badge */}
        <button
          onClick={() => setMenuOpen(true)}
          className="relative flex items-center justify-center w-10 h-10 rounded-full text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <IconSettings size={20} stroke={1.5} />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[var(--color-brand-pink)]" />
          )}
        </button>
      </header>

      {/* Slide-up navigation menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 bg-black/50" onClick={() => setMenuOpen(false)}>
          <div
            ref={menuRef}
            className="absolute bottom-0 left-0 right-0 bg-[var(--color-bg-card)] border-t border-[var(--color-border-dark)] rounded-t-2xl max-h-[85vh] overflow-y-auto animate-in slide-in-from-bottom duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 rounded-full bg-[var(--color-text-muted)]/30" />
            </div>

            {/* Close button */}
            <div className="flex items-center justify-between px-4 py-2">
              <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                {t("header.brand")}
              </span>
              <button
                onClick={() => setMenuOpen(false)}
                className="flex items-center justify-center w-8 h-8 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                title="Close menu"
              >
                <IconX size={18} />
              </button>
            </div>

            {/* Navigation */}
            <div className="px-2 py-2 pb-safe">
              {secondaryNav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-3 rounded-[var(--radius-md)] text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)] transition-colors min-h-[44px]"
                >
                  <item.icon size={20} stroke={1.5} />
                  <span>{t(item.labelKey)}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
