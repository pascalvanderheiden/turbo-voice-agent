"use client";

import { useEffect, useRef, useState } from "react";
import { VoiceOrb, type VoiceOrbState } from "@/components/voice/voice-orb";
import { useVoiceSession } from "@/lib/use-voice-session";
import { IconMicrophone, IconPlayerStop, IconEye, IconEyeOff } from "@tabler/icons-react";

export default function MobileVoicePage() {
  const {
    connectionState,
    isListening,
    isAgentSpeaking,
    audioLevel,
    transcript,
    connect,
    disconnect,
  } = useVoiceSession();

  const scrollRef = useRef<HTMLDivElement>(null);
  const [showTranscript, setShowTranscript] = useState(true);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [transcript]);

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
    if (isActive) disconnect();
    else connect("en");
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "#0F0F1A",
        color: "#fff",
        fontFamily: "system-ui, -apple-system, sans-serif",
        gap: "1.5rem",
        padding: "1rem",
        paddingTop: "3.5rem",
      }}
    >
      <VoiceOrb state={orbState} audioLevel={audioLevel} />

      <div style={{ textAlign: "center" }}>
        <p style={{ fontSize: "0.875rem", color: "#A0A0B8", minHeight: "1.25rem", margin: "0 0 0.75rem" }}>
          {connectionState === "disconnected" && "Tap to start"}
          {connectionState === "connecting" && "Connecting..."}
          {isConnected && !isListening && !isAgentSpeaking && "Listening..."}
          {isListening && "Hearing you..."}
          {isAgentSpeaking && "Responding..."}
          {connectionState === "error" && "Connection error"}
        </p>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", justifyContent: "center" }}>
          <button
            onClick={handleToggle}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.75rem 1.5rem",
              borderRadius: "1.5rem",
              border: isActive ? "1px solid rgba(239,68,68,0.3)" : "none",
              background: isActive ? "rgba(239,68,68,0.15)" : "linear-gradient(135deg, #E91E8C, #7B2FBE)",
              color: isActive ? "#ef4444" : "#fff",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isActive ? <IconPlayerStop size={18} /> : <IconMicrophone size={18} />}
            {isActive ? "End Session" : "Start Voice"}
          </button>

          <button
            onClick={() => setShowTranscript(!showTranscript)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "2.5rem",
              height: "2.5rem",
              borderRadius: "50%",
              border: "none",
              background: "#252540",
              color: "#6B6B80",
              cursor: "pointer",
            }}
          >
            {showTranscript ? <IconEye size={18} /> : <IconEyeOff size={18} />}
          </button>
        </div>
      </div>

      {showTranscript && transcript.length > 0 && (
        <div
          ref={scrollRef}
          style={{
            width: "100%",
            maxHeight: "15rem",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
            padding: "0 1rem",
          }}
        >
          {transcript.map((entry, i) => (
            <div key={i} style={{ display: "flex", justifyContent: entry.role === "user" ? "flex-end" : "flex-start" }}>
              <div
                style={{
                  maxWidth: "80%",
                  padding: "0.5rem 1rem",
                  borderRadius: "1rem",
                  fontSize: "0.875rem",
                  background: entry.role === "user" ? "rgba(233,30,140,0.15)" : "#252540",
                  color: "#fff",
                }}
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
