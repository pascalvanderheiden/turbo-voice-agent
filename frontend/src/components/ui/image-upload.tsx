"use client";

import { useCallback, useRef, useState } from "react";
import { IconUpload, IconX, IconPhoto } from "@tabler/icons-react";
import { uploadImage, getUploadUrl } from "@/lib/api";

interface ImageUploadProps {
  images: string[];
  onChange: (images: string[]) => void;
  maxImages?: number;
}

export function ImageUpload({ images, onChange, maxImages = 5 }: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const toUpload = Array.from(files).slice(0, maxImages - images.length);
      if (toUpload.length === 0) return;

      setUploading(true);
      try {
        const urls = await Promise.all(toUpload.map((f) => uploadImage(f)));
        onChange([...images, ...urls]);
      } catch {
        // silently fail — toast handled by caller if needed
      } finally {
        setUploading(false);
      }
    },
    [images, onChange, maxImages]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const removeImage = (idx: number) => {
    onChange(images.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-2">
      {/* Thumbnails */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((url, i) => (
            <div key={i} className="relative group w-16 h-16 rounded-[var(--radius-md)] overflow-hidden border border-[var(--color-border-dark)]">
              <img
                src={getUploadUrl(url)}
                alt=""
                className="w-full h-full object-cover"
              />
              <button
                onClick={() => removeImage(i)}
                className="absolute top-0 right-0 p-0.5 bg-black/60 rounded-bl text-white opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <IconX size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Hidden file input — outside the click zone to prevent event conflicts */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="sr-only"
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => {
          if (e.target.files) handleFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {/* Upload zone */}
      {images.length < maxImages && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex items-center justify-center gap-2 px-4 py-3 rounded-[var(--radius-md)] border-2 border-dashed cursor-pointer text-sm transition-colors ${
            dragOver
              ? "border-[var(--color-brand-pink)] bg-[var(--color-brand-pink)]/5"
              : "border-[var(--color-border-dark)] text-[var(--color-text-muted)] hover:border-[var(--color-text-secondary)]"
          }`}
        >
          {uploading ? (
            <span className="animate-pulse">Uploading...</span>
          ) : (
            <>
              <IconPhoto size={16} />
              <span>Drop images or click to upload</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
