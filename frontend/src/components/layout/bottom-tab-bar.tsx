"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  IconNote,
  IconBulb,
  IconSearch,
  IconFileCode,
  IconMicrophone,
  IconChecklist,
  IconMenu2,
  IconX,
  IconLayoutDashboard,
  IconCode,
  IconVideo,
  IconBolt,
  IconMessageCircle,
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const menuNav = [
  { href: "/notes", labelKey: "nav.notes", icon: IconNote },
  { href: "/todos", labelKey: "nav.todos", icon: IconChecklist },
  { href: "/ideas", labelKey: "nav.ideas", icon: IconBulb },
  { href: "/research", labelKey: "nav.research", icon: IconSearch },
  { href: "/specs", labelKey: "nav.specs", icon: IconFileCode },
  { href: "/dashboard", labelKey: "nav.dashboard", icon: IconLayoutDashboard },
  { href: "/development", labelKey: "nav.development", icon: IconCode },
  { href: "/marketing", labelKey: "nav.marketing", icon: IconVideo },
  { href: "/agents", labelKey: "nav.agents", icon: IconBolt },
  { href: "/chat", labelKey: "nav.chat", icon: IconMessageCircle },
];

export function BottomTabBar() {
  const pathname = usePathname();
  const { t } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
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

  const isVoiceActive = pathname.startsWith("/voice");

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-center bg-[var(--color-sidebar-bg)] border-t border-[var(--color-sidebar-border)] safe-area-bottom h-16">
        {/* Centered voice button */}
        <Link
          href="/voice"
          className={cn(
            "flex items-center justify-center w-14 h-14 -mt-5 rounded-full shadow-lg transition-all",
            isVoiceActive
              ? "bg-[var(--color-brand-pink)] text-white shadow-[var(--color-brand-pink)]/30"
              : "bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] text-[var(--color-text-secondary)] hover:text-[var(--color-brand-pink)] hover:border-[var(--color-brand-pink)]/40"
          )}
        >
          <IconMicrophone size={26} stroke={1.5} />
        </Link>

        {/* Hamburger menu — bottom right */}
        <button
          onClick={() => setMenuOpen(true)}
          className="absolute right-4 flex items-center justify-center w-10 h-10 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <IconMenu2 size={22} stroke={1.5} />
        </button>
      </nav>

      {/* Bottom sheet navigation menu */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/50"
          onClick={() => setMenuOpen(false)}
        >
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
              >
                <IconX size={18} />
              </button>
            </div>

            {/* Page links */}
            <div className="px-2 py-2 pb-safe">
              {menuNav.map((item) => {
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-3 rounded-[var(--radius-md)] text-sm transition-colors min-h-[44px]",
                      isActive
                        ? "bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)]"
                        : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)]"
                    )}
                  >
                    <item.icon size={20} stroke={1.5} />
                    <span>{t(item.labelKey)}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
