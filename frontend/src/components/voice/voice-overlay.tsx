"use client";

import { useRef, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useVoice } from "@/lib/voice-provider";
import { useI18n } from "@/lib/i18n";
import { useNotifications } from "@/lib/notifications";
import type { VoiceOrbState } from "@/components/voice/voice-orb";
import {
  IconPlayerStop,
  IconMaximize,
  IconChevronDown,
  IconChevronUp,
} from "@tabler/icons-react";
import styles from "./voice-overlay.module.css";

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

export function VoiceOverlay() {
  const {
    connectionState,
    isListening,
    isAgentSpeaking,
    audioLevel,
    transcript,
    activities,
    disconnect,
  } = useVoice();
  const { locale } = useI18n();
  const { addNotification } = useNotifications();
  const pathname = usePathname();
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastActivityCountRef = useRef(0);

  const isActive = connectionState === "connected" || connectionState === "connecting";
  const isOnVoicePage = pathname === "/voice";

  // Push activities to notifications
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
          if (data.success && data.note?.title) detail = ` — "${data.note.title}"`;
          else if (data.success && data.idea?.title) detail = ` — "${data.idea.title}"`;
          else if (data.notes) detail = ` — ${data.notes.length} found`;
          else if (data.ideas) detail = ` — ${data.ideas.length} found`;
          else if (data.error) detail = ` — ${data.error}`;
        } catch { /* ignore */ }
        const agent = activity.agent ?? "Agent";
        addNotification(`${agent}: ${label}${detail}`);
      }
      lastActivityCountRef.current = activities.length;
    }
  }, [activities, locale, addNotification]);

  // Auto-scroll transcript
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [transcript]);

  // Don't render overlay when on the voice page or not connected
  if (!isActive || isOnVoicePage) return null;

  const orbState: VoiceOrbState =
    connectionState === "connecting"
      ? "thinking"
      : isAgentSpeaking
        ? "speaking"
        : isListening
          ? "listening"
          : "idle";

  const statusText =
    connectionState === "connecting"
      ? "Connecting..."
      : isListening
        ? "Hearing you..."
        : isAgentSpeaking
          ? "Speaking..."
          : "Listening";

  return (
    <div className={styles.overlay} data-expanded={expanded}>
      {/* Compact bar */}
      <div className={styles.bar}>
        {/* Mini orb indicator */}
        <div className={styles.miniOrb} data-state={orbState}>
          <div className={styles.miniOrbCore} />
          <div
            className={styles.miniOrbRing}
            style={{ "--audio": Math.min(1, audioLevel).toFixed(3) } as React.CSSProperties}
          />
        </div>

        <span className={styles.status}>{statusText}</span>

        <div className={styles.controls}>
          {expanded ? (
            <button
              onClick={() => setExpanded(false)}
              className={styles.controlBtn}
              title="Collapse"
            >
              <IconChevronDown size={16} />
            </button>
          ) : (
            <button
              onClick={() => setExpanded(true)}
              className={styles.controlBtn}
              title="Expand transcript"
            >
              <IconChevronUp size={16} />
            </button>
          )}
          <button
            onClick={() => router.push("/voice")}
            className={styles.controlBtn}
            title="Open full voice mode"
          >
            <IconMaximize size={14} />
          </button>
          <button
            onClick={disconnect}
            className={`${styles.controlBtn} ${styles.stopBtn}`}
            title="Disconnect"
          >
            <IconPlayerStop size={14} />
          </button>
        </div>
      </div>

      {/* Expanded transcript panel */}
      {expanded && (
        <div ref={scrollRef} className={styles.transcript}>
          {transcript.length === 0 ? (
            <p className={styles.emptyTranscript}>Listening for your voice...</p>
          ) : (
            transcript.slice(-10).map((entry, i) => (
              <div
                key={i}
                className={`${styles.message} ${
                  entry.role === "user" ? styles.userMessage : styles.agentMessage
                }`}
              >
                {entry.text}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
