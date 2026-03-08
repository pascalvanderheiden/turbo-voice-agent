"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  IconLayoutDashboard,
  IconNote,
  IconMicrophone,
  IconMessageCircle,
  IconBulb,
  IconSearch,
  IconBolt,
  IconFileCode,
  IconCode,
  IconVideo,
  IconChevronLeft,
  IconChevronRight,
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const navItems = [
  { href: "/dashboard", labelKey: "nav.dashboard", icon: IconLayoutDashboard },
  { href: "/notes", labelKey: "nav.notes", icon: IconNote },
  { href: "/ideas", labelKey: "nav.ideas", icon: IconBulb },
  { href: "/research", labelKey: "nav.research", icon: IconSearch },
  { href: "/specs", labelKey: "nav.specs", icon: IconFileCode },
  { href: "/development", labelKey: "nav.development", icon: IconCode },
  { href: "/marketing", labelKey: "nav.marketing", icon: IconVideo },
  { href: "/agents", labelKey: "nav.agents", icon: IconBolt },
  { href: "/voice", labelKey: "nav.voice", icon: IconMicrophone },
  { href: "/chat", labelKey: "nav.chat", icon: IconMessageCircle },
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <aside
      className={cn(
        "flex flex-col border-r transition-all duration-200",
        "bg-[var(--color-sidebar-bg)] border-[var(--color-sidebar-border)]",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-[var(--color-sidebar-border)]">
        <Image src="/logo.png" alt="Turbo Agent" width={32} height={32} className="flex-shrink-0" />
        {!collapsed && (
          <span className="font-semibold text-sm gradient-brand-text">Turbo Agent</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-[var(--radius-md)] text-sm transition-colors",
                isActive
                  ? "bg-[var(--color-brand-pink)]/10 text-[var(--color-brand-pink)]"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)]"
              )}
            >
              <item.icon size={20} stroke={1.5} />
              {!collapsed && <span>{t(item.labelKey)}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-[var(--color-sidebar-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
      >
        {collapsed ? <IconChevronRight size={16} /> : <IconChevronLeft size={16} />}
      </button>
    </aside>
  );
}
