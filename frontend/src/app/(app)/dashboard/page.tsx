"use client";

import { IconNote, IconMicrophone, IconBolt, IconBulb, IconSearch, IconFileCode, IconCode, IconVideo } from "@tabler/icons-react";
import { useI18n } from "@/lib/i18n";

export default function DashboardPage() {
  const { t } = useI18n();

  const cards = [
    { icon: IconNote, label: t("dashboard.notesLabel"), desc: t("dashboard.notesDesc"), href: "/notes", color: "var(--color-brand-cyan)" },
    { icon: IconBulb, label: t("dashboard.ideasLabel"), desc: t("dashboard.ideasDesc"), href: "/ideas", color: "var(--color-brand-purple)" },
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
        {cards.map((card) => (
          <a
            key={card.href}
            href={card.href}
            className="flex items-start gap-4 p-5 rounded-[var(--radius-lg)] bg-[var(--color-bg-card)] border border-[var(--color-border-dark)] hover:border-[var(--color-brand-pink)]/30 transition-colors"
          >
            <div
              className="flex items-center justify-center w-10 h-10 rounded-[var(--radius-md)]"
              style={{ backgroundColor: `${card.color}15`, color: card.color }}
            >
              <card.icon size={22} stroke={1.5} />
            </div>
            <div>
              <h3 className="font-medium text-sm">{card.label}</h3>
              <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{card.desc}</p>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
