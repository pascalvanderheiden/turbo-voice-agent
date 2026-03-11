"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getVoiceWebSocketUrl, getVoiceAccessToken } from "@/lib/api";
import type { Locale } from "@/lib/i18n";

export type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

interface TranscriptEntry {
  role: "user" | "agent";
  text: string;
}

export interface AgentActivity {
  id: string;
  action: string;
  status: "started" | "completed";
  agent?: string;
  output?: string;
  timestamp: number;
}

interface VoiceContextValue {
  connectionState: ConnectionState;
  isListening: boolean;
  isAgentSpeaking: boolean;
  audioLevel: number;
  transcript: TranscriptEntry[];
  activities: AgentActivity[];
  connect: (locale?: Locale) => Promise<void>;
  disconnect: () => void;
}

const VoiceContext = createContext<VoiceContextValue | null>(null);

export function useVoice() {
  const ctx = useContext(VoiceContext);
  if (!ctx) throw new Error("useVoice must be used within VoiceProvider");
  return ctx;
}

export function VoiceProvider({ children }: { children: React.ReactNode }) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [isListening, setIsListening] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [activities, setActivities] = useState<AgentActivity[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const isPlayingRef = useRef(false);
  const playbackQueueRef = useRef<ArrayBuffer[]>([]);
  const playbackTimeRef = useRef(0);
  const agentTranscriptRef = useRef("");
  const intentionalDisconnectRef = useRef(false);
  const connectionStateRef = useRef<ConnectionState>("disconnected");
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);

  const updateConnectionState = useCallback((state: ConnectionState) => {
    connectionStateRef.current = state;
    setConnectionState(state);
  }, []);

  // Screen Wake Lock — keeps screen on during voice sessions
  const acquireWakeLock = useCallback(async () => {
    if (!("wakeLock" in navigator)) return;
    try {
      wakeLockRef.current = await navigator.wakeLock.request("screen");
      wakeLockRef.current.addEventListener("release", () => { wakeLockRef.current = null; });
    } catch { /* wake lock not available or denied */ }
  }, []);

  const releaseWakeLock = useCallback(() => {
    wakeLockRef.current?.release();
    wakeLockRef.current = null;
  }, []);

  // Visibility change — resume AudioContext & re-acquire wake lock when returning to the app
  useEffect(() => {
    const handleVisibilityChange = async () => {
      if (document.visibilityState === "visible") {
        // Resume suspended AudioContext (browsers suspend on tab hide / lock screen)
        if (audioContextRef.current?.state === "suspended") {
          try { await audioContextRef.current.resume(); } catch { /* ignore */ }
        }
        // Re-acquire wake lock (released by OS when page goes hidden)
        if (connectionStateRef.current === "connected") {
          acquireWakeLock();
        }
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [acquireWakeLock]);

  const playAudioQueue = useCallback((ctx: AudioContext) => {
    if (isPlayingRef.current) return;
    isPlayingRef.current = true;

    const drain = () => {
      if (playbackQueueRef.current.length === 0) {
        isPlayingRef.current = false;
        return;
      }
      const buf = playbackQueueRef.current.shift()!;
      const pcm16 = new Int16Array(buf);
      const float32 = new Float32Array(pcm16.length);
      for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / 32768;
      }
      const audioBuffer = ctx.createBuffer(1, float32.length, 24000);
      audioBuffer.getChannelData(0).set(float32);

      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      const now = ctx.currentTime;
      const startTime = Math.max(now, playbackTimeRef.current);
      playbackTimeRef.current = startTime + audioBuffer.duration;
      source.start(startTime);
      source.onended = drain;
    };
    drain();
  }, []);

  const cleanupResources = useCallback(() => {
    intentionalDisconnectRef.current = true;
    releaseWakeLock();
    try { processorRef.current?.disconnect(); } catch {}
    try { streamRef.current?.getTracks().forEach((t) => t.stop()); } catch {}
    try { audioContextRef.current?.close(); } catch {}
    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      ws.onclose = null;
      ws.onerror = null;
      ws.onmessage = null;
      try { ws.close(); } catch {}
    }
    playbackQueueRef.current = [];
    playbackTimeRef.current = 0;
    isPlayingRef.current = false;
    updateConnectionState("disconnected");
    setIsListening(false);
    setIsAgentSpeaking(false);
    setAudioLevel(0);
  }, [updateConnectionState, releaseWakeLock]);

  const connect = useCallback(async (locale?: Locale) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    updateConnectionState("connecting");
    intentionalDisconnectRef.current = false;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 24000, channelCount: 1, echoCancellation: true },
      });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 24000 });
      audioContextRef.current = audioContext;
      playbackTimeRef.current = 0;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(2048, 1, 1);
      processorRef.current = processor;

      const token = await getVoiceAccessToken();
      const params = new URLSearchParams();
      if (locale) params.set("lang", locale);
      if (token) params.set("token", token);
      const qs = params.toString();
      const wsUrl = qs ? `${getVoiceWebSocketUrl()}?${qs}` : getVoiceWebSocketUrl();
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        updateConnectionState("connecting");
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case "session.ready":
            updateConnectionState("connected");
            acquireWakeLock();
            processor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              let sum = 0;
              for (let i = 0; i < inputData.length; i++) {
                sum += inputData[i] * inputData[i];
              }
              setAudioLevel(Math.sqrt(sum / inputData.length));

              const pcm16 = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) {
                pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
              }
              const bytes = new Uint8Array(pcm16.buffer);
              let binary = "";
              for (let i = 0; i < bytes.length; i++) {
                binary += String.fromCharCode(bytes[i]);
              }
              const base64 = btoa(binary);
              if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "input_audio", audio: base64 }));
              }
            };
            source.connect(processor);
            processor.connect(audioContext.destination);
            break;

          case "input_audio_buffer.speech_started":
            setIsListening(true);
            setIsAgentSpeaking(false);
            playbackQueueRef.current = [];
            playbackTimeRef.current = 0;
            break;

          case "input_audio_buffer.speech_stopped":
            setIsListening(false);
            break;

          case "input_audio_transcription.done":
            if (msg.transcript) {
              setTranscript((prev) => [...prev, { role: "user", text: msg.transcript }]);
            }
            break;

          case "response.audio.delta": {
            setIsAgentSpeaking(true);
            const binaryStr = atob(msg.audio);
            const audioBytes = new Uint8Array(binaryStr.length);
            for (let i = 0; i < binaryStr.length; i++) {
              audioBytes[i] = binaryStr.charCodeAt(i);
            }
            playbackQueueRef.current.push(audioBytes.buffer);
            playAudioQueue(audioContext);
            break;
          }

          case "response.audio_transcript.delta":
            agentTranscriptRef.current += msg.transcript;
            break;

          case "response.audio_transcript.done":
            if (msg.transcript) {
              setTranscript((prev) => [...prev, { role: "agent", text: msg.transcript }]);
            }
            agentTranscriptRef.current = "";
            break;

          case "response.done":
            setIsAgentSpeaking(false);
            break;

          case "agent.activity":
            console.log("[voice] Agent activity:", msg.action, msg.status);
            setActivities((prev) => [
              ...prev,
              {
                id: `${msg.action}-${Date.now()}`,
                action: msg.action,
                status: msg.status,
                agent: msg.agent,
                output: msg.output,
                timestamp: Date.now(),
              },
            ]);
            break;

          case "session.end":
            cleanupResources();
            break;

          case "error":
            if (connectionStateRef.current === "connecting") {
              updateConnectionState("error");
            }
            console.warn("[voice] Non-fatal error:", msg.message);
            break;
        }
      };

      ws.onerror = () => updateConnectionState("error");
      ws.onclose = () => {
        if (!intentionalDisconnectRef.current) {
          updateConnectionState("disconnected");
          setIsListening(false);
          setIsAgentSpeaking(false);
          setAudioLevel(0);
        }
      };
    } catch {
      updateConnectionState("error");
    }
  }, [playAudioQueue, updateConnectionState, cleanupResources, acquireWakeLock]);

  const disconnect = useCallback(() => {
    cleanupResources();
  }, [cleanupResources]);

  // No cleanup on unmount — provider lives for app lifetime

  return (
    <VoiceContext.Provider
      value={{
        connectionState,
        isListening,
        isAgentSpeaking,
        audioLevel,
        transcript,
        activities,
        connect,
        disconnect,
      }}
    >
      {children}
    </VoiceContext.Provider>
  );
}
