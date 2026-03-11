"use client";

import { useEffect, useRef, useState } from "react";
import { VoiceOrb, type VoiceOrbState } from "@/components/voice/voice-orb";
import { useVoice } from "@/lib/voice-provider";
import { useI18n } from "@/lib/i18n";
import { useNotifications } from "@/lib/notifications";
import { IconMicrophone, IconPlayerStop, IconEye, IconEyeOff } from "@tabler/icons-react";
import { useIsMobile } from "@/hooks/use-is-mobile";

const ACTION_LABELS: Record<string, Record<string, string>> = {
  en: {
    get_notes: "Retrieve notes",
    get_note: "Retrieve note",
    create_note: "Create note",
    update_note: "Update note",
    delete_note: "Delete note",
    get_ideas: "Retrieve ideas",
    get_idea: "Retrieve idea",
    create_idea: "Create idea",
    update_idea: "Update idea",
    delete_idea: "Delete idea",
    refine_idea: "Refine idea",
    web_search: "Web search",
    deep_research: "Deep research",
    get_research_list: "Retrieve research",
    get_research: "Retrieve research",
    delete_research: "Delete research",
    create_spec: "Create spec",
    get_specs: "Retrieve specs",
    get_spec: "Retrieve spec",
    update_spec: "Update spec",
    delete_spec: "Delete spec",
    generate_spec: "Generate specs",
    optimize_spec: "Optimize spec",
  },
  nl: {
    get_notes: "Notities ophalen",
    get_note: "Notitie ophalen",
    create_note: "Notitie aanmaken",
    update_note: "Notitie bijwerken",
    delete_note: "Notitie verwijderen",
    get_ideas: "Ideeën ophalen",
    get_idea: "Idee ophalen",
    create_idea: "Idee aanmaken",
    update_idea: "Idee bijwerken",
    delete_idea: "Idee verwijderen",
    refine_idea: "Idee verfijnen",
    web_search: "Webzoekopdracht",
    deep_research: "Diep onderzoek",
    get_research_list: "Onderzoek ophalen",
    get_research: "Onderzoek ophalen",
    delete_research: "Onderzoek verwijderen",
    create_spec: "Spec aanmaken",
    get_specs: "Specs ophalen",
    get_spec: "Spec ophalen",
    update_spec: "Spec bijwerken",
    delete_spec: "Spec verwijderen",
    generate_spec: "Specs genereren",
    optimize_spec: "Spec optimaliseren",
  },
};

export default function VoicePage() {
  const {
    connectionState,
    isListening,
    isAgentSpeaking,
    audioLevel,
    transcript,
    activities,
    connect,
    disconnect,
  } = useVoice();

  const { locale, t } = useI18n();
  const { addNotification } = useNotifications();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showTranscript, setShowTranscript] = useState(true);
  const lastActivityCountRef = useRef(0);
  const isMobile = useIsMobile();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [transcript]);

  // Push new activities to notification system (only completed, not started)
  useEffect(() => {
    if (activities.length > lastActivityCountRef.current) {
      const newItems = activities.slice(lastActivityCountRef.current);
      for (const activity of newItems) {
        if (activity.status !== "completed") continue;
        const labels = ACTION_LABELS[locale] ?? ACTION_LABELS.en;
        const label = labels[activity.action] ?? activity.action;
        let detail = "";
        try {
          const data = JSON.parse(activity.output ?? "{}");
          if (data.success && data.note?.title) {
            detail = ` — "${data.note.title}"`;
          } else if (data.success && data.idea?.title) {
            detail = ` — "${data.idea.title}"`;
          } else if (data.notes) {
            detail = locale === "nl" ? ` — ${data.notes.length} gevonden` : ` — ${data.notes.length} found`;
          } else if (data.ideas) {
            detail = locale === "nl" ? ` — ${data.ideas.length} gevonden` : ` — ${data.ideas.length} found`;
          } else if (data.error) {
            detail = ` — ${data.error}`;
          }
        } catch { /* ignore */ }
        const agent = activity.agent ?? "Agent";
        addNotification(`${agent}: ${label}${detail}`);
      }
      lastActivityCountRef.current = activities.length;
    }
  }, [activities, locale, addNotification]);

  const orbState: VoiceOrbState =
    connectionState === "error"
      ? "error"
      : connectionState === "connecting"
        ? "thinking"
        : isAgentSpeaking
          ? "speaking"
          : isListening
            ? "listening"
            : connectionState === "connected"
              ? "idle"
              : "idle";

  const isConnected = connectionState === "connected";
  const isActive = isConnected || connectionState === "connecting";

  const handleToggle = () => {
    if (isActive) {
      disconnect();
    } else {
      connect(locale);
    }
  };

  return (
    <div className={`flex flex-col items-center justify-center h-full space-y-6 ${
      isMobile ? "-mt-4 pb-4" : "-mt-14"
    }`}>
      {/* Voice Orb — larger on mobile */}
      <div className={isMobile ? "scale-[1.4]" : ""}>
        <VoiceOrb state={orbState} audioLevel={audioLevel} />
      </div>

      {/* Status + Button */}
      <div className="text-center space-y-3">
        <p className="text-sm text-[var(--color-text-secondary)] min-h-[1.25rem]">
          {connectionState === "disconnected" && t("voice.tapToStart")}
          {connectionState === "connecting" && t("voice.connecting")}
          {connectionState === "connected" && !isListening && !isAgentSpeaking && t("voice.listening")}
          {isListening && t("voice.hearing")}
          {isAgentSpeaking && t("voice.responding")}
          {connectionState === "error" && t("voice.error")}
        </p>

        <div className="flex items-center gap-3 justify-center">
          <button
            onClick={handleToggle}
            className={`flex items-center gap-2 px-6 py-3 rounded-full text-sm font-semibold transition-all duration-300 ${
              isActive
                ? "bg-red-500/15 text-red-400 hover:bg-red-500/25 border border-red-500/30"
                : "text-white hover:opacity-90 shadow-lg shadow-[var(--color-brand-pink)]/25"
            }`}
            style={
              !isActive
                ? { background: "linear-gradient(135deg, #E91E8C, #7B2FBE)" }
                : undefined
            }
          >
            {isActive ? (
              <>
                <IconPlayerStop size={18} /> {t("voice.stop")}
              </>
            ) : (
              <>
                <IconMicrophone size={18} /> {t("voice.start")}
              </>
            )}
          </button>

          {/* Hide/show transcript toggle */}
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="flex items-center justify-center w-10 h-10 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
            title={showTranscript ? t("voice.hideTranscript") : t("voice.showTranscript")}
          >
            {showTranscript ? <IconEye size={18} /> : <IconEyeOff size={18} />}
          </button>
        </div>
      </div>

      {/* Transcript */}
      {showTranscript && transcript.length > 0 && (
        <div
          ref={scrollRef}
          className={`w-full max-w-lg space-y-3 overflow-y-auto px-4 ${
            isMobile ? "max-h-40" : "max-h-60"
          }`}
        >
          {transcript.map((entry, i) => (
            <div
              key={i}
              className={`flex ${entry.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm ${
                  entry.role === "user"
                    ? "bg-[var(--color-brand-pink)]/15 text-[var(--color-text-primary)]"
                    : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                }`}
              >
                {entry.text}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
