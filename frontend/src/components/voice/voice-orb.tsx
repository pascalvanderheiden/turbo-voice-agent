"use client";

import { useEffect, useRef } from "react";
import styles from "./voice-orb.module.css";

export type VoiceOrbState = "idle" | "listening" | "thinking" | "speaking" | "error";

interface VoiceOrbProps {
  state: VoiceOrbState;
  audioLevel?: number;
}

export function VoiceOrb({ state, audioLevel = 0 }: VoiceOrbProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const clamped = Math.min(1, Math.max(0, audioLevel));
    el.style.setProperty("--audio", clamped.toFixed(3));
  }, [audioLevel]);

  return (
    <div
      ref={containerRef}
      className={styles.root}
      data-state={state}
      aria-label={`Voice agent: ${state}`}
      style={{ "--audio": "0" } as React.CSSProperties}
    >
      <div className={styles.glow} />
      <div className={styles.wave} />
      <div className={styles.core}>
        <div className={styles.shine} />
      </div>
    </div>
  );
}
