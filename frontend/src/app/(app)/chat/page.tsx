"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { IconSend, IconLoader2 } from "@tabler/icons-react";
import { useNotifications } from "@/lib/notifications";
import { useI18n } from "@/lib/i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

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

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { addNotification } = useNotifications();
  const { locale, t } = useI18n();

  // Auto-scroll to latest message
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-u`,
      role: "user",
      content: text,
    };

    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setIsLoading(true);

    // Reset textarea height
    if (inputRef.current) inputRef.current.style.height = "auto";

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: updatedMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}-a`,
        role: "assistant",
        content: data.reply ?? "…",
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Show toast notifications for tool calls
      if (data.tool_calls && Array.isArray(data.tool_calls)) {
        const labels = ACTION_LABELS[locale] ?? ACTION_LABELS.en;
        for (const tc of data.tool_calls) {
          const label = labels[tc.action] ?? tc.action;
          const agent = tc.agent ?? "Agent";
          const detail = tc.summary ? ` — ${tc.summary}` : "";
          addNotification(`${agent}: ${label}${detail}`);
        }
      }
    } catch {
      const errorMsg: ChatMessage = {
        id: `msg-${Date.now()}-e`,
        role: "assistant",
        content: t("chat.error"),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages, locale, addNotification, t]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize textarea
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto space-y-4">
          {/* Welcome message */}
          {messages.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full min-h-[50vh] space-y-4">
              {/* Mini gradient orb */}
              <div
                className="w-16 h-16 rounded-full opacity-80"
                style={{
                  background: "radial-gradient(circle at 35% 35%, #E91E8C, #7B2FBE 60%, #00D4FF)",
                  boxShadow: "0 0 40px rgba(233,30,140,0.3), 0 0 80px rgba(123,47,190,0.15)",
                }}
              />
              <p className="text-lg font-semibold text-[var(--color-text-primary)]">
                {t("chat.welcome")}
              </p>
              <p className="text-sm text-[var(--color-text-secondary)]">
                {t("chat.welcomeHint")}
              </p>
            </div>
          )}

          {/* Chat messages */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div
                  className="w-7 h-7 rounded-full flex-shrink-0 mt-1 mr-2"
                  style={{
                    background: "radial-gradient(circle at 35% 35%, #E91E8C, #7B2FBE 60%, #00D4FF)",
                  }}
                />
              )}
              <div
                className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-[var(--color-brand-pink)]/15 text-[var(--color-text-primary)]"
                    : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div
                className="w-7 h-7 rounded-full flex-shrink-0 mt-1 mr-2"
                style={{
                  background: "radial-gradient(circle at 35% 35%, #E91E8C, #7B2FBE 60%, #00D4FF)",
                }}
              />
              <div className="bg-[var(--color-bg-tertiary)] px-4 py-2.5 rounded-2xl text-sm text-[var(--color-text-secondary)] flex items-center gap-2">
                <IconLoader2 size={14} className="animate-spin" />
                {t("chat.thinking")}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input bar */}
      <div className="border-t border-[var(--color-border-dark)] bg-[var(--color-bg-secondary)] px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={t("chat.placeholder")}
            rows={1}
            disabled={isLoading}
            className="flex-1 resize-none bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] rounded-xl px-4 py-2.5 text-sm outline-none border border-[var(--color-border-dark)] focus:border-[var(--color-brand-pink)]/50 transition-colors"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="flex items-center justify-center w-10 h-10 rounded-xl text-white transition-opacity disabled:opacity-30"
            style={{ background: "linear-gradient(135deg, #E91E8C, #7B2FBE)" }}
          >
            <IconSend size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
