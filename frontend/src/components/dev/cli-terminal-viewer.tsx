"use client";

import { useEffect, useRef, useState } from "react";
import { IconTerminal } from "@tabler/icons-react";

interface CliTerminalViewerProps {
  taskId: string;
  apiUrl?: string;
}

export function CliTerminalViewer({ taskId, apiUrl }: CliTerminalViewerProps) {
  const [lines, setLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const baseUrl = apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const es = new EventSource(`${baseUrl}/api/sandbox/tasks/${taskId}/stream`);
    setConnected(true);

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "output" && data.text) {
          setLines((prev) => [...prev, data.text]);
        } else if (data.type === "complete") {
          setConnected(false);
          es.close();
        }
      } catch {
        setLines((prev) => [...prev, event.data]);
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
    };

    return () => es.close();
  }, [taskId, baseUrl]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [lines]);

  return (
    <div className="rounded-xl border border-white/10 bg-black/60 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10 bg-white/5">
        <IconTerminal className="w-4 h-4 text-cyan-400" />
        <span className="text-xs font-medium text-gray-400">Copilot CLI</span>
        {connected && (
          <span className="ml-auto flex items-center gap-1 text-xs text-green-400">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Live
          </span>
        )}
      </div>
      <div ref={scrollRef} className="p-4 h-64 overflow-y-auto font-mono text-xs text-green-300 leading-relaxed">
        {lines.length === 0 ? (
          <span className="text-gray-600">Waiting for output...</span>
        ) : (
          lines.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap">{line}</div>
          ))
        )}
      </div>
    </div>
  );
}
