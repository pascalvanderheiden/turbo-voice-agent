"use client";

import { useCallback, useRef, useState } from "react";
import { IconUpload, IconX, IconPhoto, IconFileTypePdf } from "@tabler/icons-react";
import { uploadImage, getUploadUrl } from "@/lib/api";
import { toast } from "sonner";

interface ImageUploadProps {
  images: string[];
  onChange: (images: string[]) => void;
  attachments?: string[];
  onAttachmentsChange?: (attachments: string[]) => void;
  maxImages?: number;
  maxAttachments?: number;
  acceptPdf?: boolean;
}

function isPdf(url: string): boolean {
  return url.toLowerCase().endsWith(".pdf");
}

export function ImageUpload({
  images,
  onChange,
  attachments = [],
  onAttachmentsChange,
  maxImages = 5,
  maxAttachments = 5,
  acceptPdf = false,
}: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      setError(null);
      const fileArray = Array.from(files);
      const isPdfFile = (f: File) =>
        f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf");
      const imageFiles = fileArray.filter((f) => f.type.startsWith("image/"));
      const pdfFiles = acceptPdf ? fileArray.filter((f) => isPdfFile(f) && !f.type.startsWith("image/")) : [];

      const imagesToUpload = imageFiles.slice(0, maxImages - images.length);
      const pdfsToUpload = pdfFiles.slice(0, maxAttachments - attachments.length);

      if (imagesToUpload.length === 0 && pdfsToUpload.length === 0) {
        if (fileArray.length > 0) {
          const names = fileArray.map((f) => f.name).join(", ");
          const msg = `Unsupported file type: ${names}`;
          setError(msg);
          toast.error(msg);
        }
        return;
      }

      setUploading(true);
      try {
        const allUploads = await Promise.all(
          [...imagesToUpload, ...pdfsToUpload].map((f) => uploadImage(f))
        );
        const newImageUrls = allUploads.slice(0, imagesToUpload.length);
        const newPdfUrls = allUploads.slice(imagesToUpload.length);

        if (newImageUrls.length > 0) {
          onChange([...images, ...newImageUrls]);
        }
        if (newPdfUrls.length > 0 && onAttachmentsChange) {
          onAttachmentsChange([...attachments, ...newPdfUrls]);
        }
      } catch (err) {
        const msg = `Upload failed: ${err instanceof Error ? err.message : String(err)}`;
        setError(msg);
        toast.error(msg);
      } finally {
        setUploading(false);
      }
    },
    [images, onChange, attachments, onAttachmentsChange, maxImages, maxAttachments, acceptPdf]
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

  const removeAttachment = (idx: number) => {
    if (onAttachmentsChange) {
      onAttachmentsChange(attachments.filter((_, i) => i !== idx));
    }
  };

  const acceptTypes = acceptPdf ? "image/*,application/pdf,.pdf" : "image/*";
  const totalSlots = images.length + attachments.length;
  const maxTotal = maxImages + maxAttachments;

  return (
    <div className="space-y-2">
      {/* Image thumbnails */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((url, i) => (
            <div key={`img-${i}`} className="relative group w-16 h-16 rounded-[var(--radius-md)] overflow-hidden border border-[var(--color-border-dark)]">
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

      {/* PDF attachment chips */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {attachments.map((url, i) => {
            const name = url.split("/").pop() || "document.pdf";
            const shortName = name.length > 20 ? name.slice(0, 17) + "..." : name;
            return (
              <div
                key={`pdf-${i}`}
                className="group flex items-center gap-1.5 px-2.5 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-dark)] text-xs"
              >
                <IconFileTypePdf size={14} className="text-red-400 shrink-0" />
                <span className="text-[var(--color-text-secondary)] truncate max-w-[120px]">{shortName}</span>
                <button
                  onClick={() => removeAttachment(i)}
                  className="p-0.5 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 hover:text-white transition-all"
                >
                  <IconX size={10} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept={acceptTypes}
        multiple
        className="sr-only"
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => {
          if (e.target.files) handleFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {/* Upload zone */}
      {totalSlots < maxTotal && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex items-center justify-center gap-2 px-4 py-3 rounded-[var(--radius-md)] border-2 border-dashed cursor-pointer text-sm transition-colors ${
            dragOver
              ? "border-[var(--color-brand-pink)] bg-[var(--color-brand-pink)]/5"
              : error
                ? "border-red-500/50 text-red-400"
                : "border-[var(--color-border-dark)] text-[var(--color-text-muted)] hover:border-[var(--color-text-secondary)]"
          }`}
        >
          {uploading ? (
            <span className="animate-pulse">Uploading...</span>
          ) : (
            <>
              <IconPhoto size={16} />
              <span>{acceptPdf ? "Drop images or PDFs, or click to upload" : "Drop images or click to upload"}</span>
            </>
          )}
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
