"use client";

import { useEffect, useState } from "react";
import { IconNote, IconMicrophone, IconBolt, IconBulb, IconSearch, IconFileCode, IconCode, IconVideo, IconChecklist, IconPresentation } from "@tabler/icons-react";
import { useI18n } from "@/lib/i18n";
import { notesApi, ideasApi, researchApi, specsApi, devApi, marketingApi, todosApi, slidesApi } from "@/lib/api";

export default function DashboardPage() {
  const { t } = useI18n();
  const [counts, setCounts] = useState<Record<string, number | null>>({});

  useEffect(() => {
    const load = async () => {
      const [notes, ideas, research, specs, dev, marketing, todos, slides] = await Promise.all([
        notesApi.list().then((r) => r.length).catch(() => null),
        ideasApi.list().then((r) => r.length).catch(() => null),
        researchApi.list().then((r) => r.length).catch(() => null),
        specsApi.list().then((r) => r.length).catch(() => null),
        devApi.list().then((r) => r.length).catch(() => null),
        marketingApi.list().then((r) => r.length).catch(() => null),
        todosApi.list().then((r) => r.length).catch(() => null),
        slidesApi.list().then((r) => r.length).catch(() => null),
      ]);
      setCounts({ "/notes": notes, "/ideas": ideas, "/research": research, "/specs": specs, "/development": dev, "/marketing": marketing, "/todos": todos, "/slides": slides });
    };
    load();
  }, []);

  const cards = [
    { icon: IconNote, label: t("dashboard.notesLabel"), desc: t("dashboard.notesDesc"), href: "/notes", color: "var(--color-brand-cyan)" },
    { icon: IconChecklist, label: t("dashboard.todosLabel"), desc: t("dashboard.todosDesc"), href: "/todos", color: "var(--color-brand-cyan)" },
    { icon: IconBulb, label: t("dashboard.ideasLabel"), desc: t("dashboard.ideasDesc"), href: "/ideas", color: "var(--color-brand-purple)" },
    { icon: IconPresentation, label: t("dashboard.slidesLabel"), desc: t("dashboard.slidesDesc"), href: "/slides", color: "var(--color-brand-purple)" },
    { icon: IconSearch, label: t("dashboard.researchLabel"), desc: t("dashboard.researchDesc"), href: "/research", color: "var(--color-brand-cyan)" },
    { icon: IconFileCode, label: t("dashboard.specsLabel"), desc: t("dashboard.specsDesc"), href: "/specs", color: "var(--color-brand-pink)" },
    { icon: IconCode, label: t("dashboard.devLabel"), desc: t("dashboard.devDesc"), href: "/development", color: "var(--color-brand-pink)" },
    { icon: IconVideo, label: t("dashboard.marketingLabel"), desc: t("dashboard.marketingDesc"), href: "/marketing", color: "var(--color-brand-purple)" },
    { icon: IconMicrophone, label: t("dashboard.voiceLabel"), desc: t("dashboard.voiceDesc"), href: "/voice", color: "var(--color-brand-pink)" },
    { icon: IconBolt, label: t("dashboard.agentLabel"), desc: t("dashboard.agentDesc"), href: "/agents", color: "var(--color-brand-purple)" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold gradient-brand-text">{t("dashboard.title")}</h1>
        <p className="text-[var(--color-text-secondary)] mt-1">
          {t("dashboard.welcome")}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map((card) => {
          const count = counts[card.href];
          return (
            <a
              key={card.href}
              href={card.href}
              className="flex items-start gap-4 p-5 rounded-[var(--radius-lg)] bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] hover:border-[var(--color-brand-pink)]/30 transition-colors"
            >
              <div
                className="relative flex items-center justify-center w-10 h-10 rounded-[var(--radius-md)]"
                style={{ backgroundColor: `${card.color}15`, color: card.color }}
              >
                <card.icon size={22} stroke={1.5} />
                {count != null && (
                  <span
                    className="absolute -top-1.5 -right-1.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white rounded-full"
                    style={{ backgroundColor: card.color }}
                  >
                    {count > 99 ? "99+" : count}
                  </span>
                )}
              </div>
              <div>
                <h3 className="font-medium text-sm">{card.label}</h3>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{card.desc}</p>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}
