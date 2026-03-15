"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  IconNote,
  IconBulb,
  IconSearch,
  IconFileCode,
  IconMicrophone,
  IconChecklist,
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const tabs = [
  { href: "/notes", labelKey: "nav.notes", icon: IconNote },
  { href: "/todos", labelKey: "nav.todos", icon: IconChecklist },
  { href: "/ideas", labelKey: "nav.ideas", icon: IconBulb },
  { href: "/research", labelKey: "nav.research", icon: IconSearch },
  { href: "/specs", labelKey: "nav.specs", icon: IconFileCode },
  { href: "/voice", labelKey: "nav.voice", icon: IconMicrophone },
];

export function BottomTabBar() {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around bg-[var(--color-sidebar-bg)] border-t border-[var(--color-sidebar-border)] safe-area-bottom">
      {tabs.map((tab) => {
        const isActive = pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "flex flex-col items-center justify-center gap-0.5 min-w-[44px] min-h-[44px] py-2 px-3 text-xs transition-colors",
              isActive
                ? "text-[var(--color-brand-pink)]"
                : "text-[var(--color-text-muted)]"
            )}
          >
            <tab.icon size={22} stroke={1.5} />
            <span className="text-[10px] leading-tight">{t(tab.labelKey)}</span>
            {isActive && (
              <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-[var(--color-brand-pink)]" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
