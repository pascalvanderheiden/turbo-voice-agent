"use client";

import { useState } from "react";
import { IconPhoto, IconX } from "@tabler/icons-react";

interface ScreenshotGalleryProps {
  screenshots: string[];
  className?: string;
}

export function ScreenshotGallery({ screenshots, className }: ScreenshotGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  if (!screenshots.length) return null;

  return (
    <>
      <div className={`rounded-xl border border-white/10 bg-white/5 p-4 ${className || ""}`}>
        <div className="flex items-center gap-2 mb-3">
          <IconPhoto className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-medium text-white">Screenshots ({screenshots.length})</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {screenshots.map((src, i) => (
            <button
              key={i}
              onClick={() => setSelectedIndex(i)}
              className="aspect-video rounded-lg border border-white/10 overflow-hidden hover:border-cyan-400 transition-colors"
            >
              <img src={src} alt={`Screenshot ${i + 1}`} className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      </div>

      {/* Lightbox */}
      {selectedIndex !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setSelectedIndex(null)}
        >
          <button
            onClick={() => setSelectedIndex(null)}
            className="absolute top-4 right-4 text-white/60 hover:text-white"
          >
            <IconX className="w-6 h-6" />
          </button>
          <img
            src={screenshots[selectedIndex]}
            alt={`Screenshot ${selectedIndex + 1}`}
            className="max-w-[90vw] max-h-[90vh] rounded-lg shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
}
