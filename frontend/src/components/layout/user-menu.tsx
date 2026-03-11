"use client";

import { useEffect, useRef, useState } from "react";
import { IconChevronDown, IconChevronUp, IconLanguage, IconLogout, IconCamera, IconSun, IconMoon } from "@tabler/icons-react";
import { useI18n, type Locale } from "@/lib/i18n";
import { useTheme } from "next-themes";
import { userApi, profileApi } from "@/lib/api";

interface UserMenuProps {
  displayName: string;
  email: string;
  photoUrl?: string | null;
  onPhotoChange?: (url: string) => void;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function UserMenu({ displayName, email, photoUrl, onPhotoChange }: UserMenuProps) {
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [currentPhotoUrl, setCurrentPhotoUrl] = useState(photoUrl);
  const [mounted, setMounted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    setCurrentPhotoUrl(photoUrl);
  }, [photoUrl]);

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await userApi.uploadPhoto(file);
      // Always re-fetch the photo through the authenticated API proxy
      // to get a displayable object URL (avoids CORS / relative-path issues)
      const objectUrl = await userApi.getPhotoObjectUrl();
      if (objectUrl) {
        setCurrentPhotoUrl(objectUrl);
        onPhotoChange?.(objectUrl);
      }
    } catch (err) {
      console.error("Photo upload failed:", err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleToggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    profileApi.updateProfile({ theme: next }).catch(() => {});
  };

  const handleLogout = () => {
    const clientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID;
    if (clientId) {
      import("@/lib/msal-config").then(({ getMsalInstance }) => {
        const instance = getMsalInstance();
        instance.logoutRedirect();
      });
    }
  };

  return (
    <div className="w-full">
      {/* Profile trigger — expand/collapse inline */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-2 h-9 rounded-full text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
      >
        {currentPhotoUrl ? (
          <img
            src={currentPhotoUrl}
            alt={displayName}
            className="w-6 h-6 rounded-full object-cover"
          />
        ) : (
          <div className="w-6 h-6 rounded-full bg-[var(--color-brand-pink)]/20 text-[var(--color-brand-pink)] flex items-center justify-center text-[10px] font-bold">
            {getInitials(displayName || email)}
          </div>
        )}
        <span className="text-xs font-medium max-w-[120px] truncate">
          {displayName || email}
        </span>
        {open ? <IconChevronUp size={14} stroke={1.5} className="ml-auto" /> : <IconChevronDown size={14} stroke={1.5} className="ml-auto" />}
      </button>

      {/* Inline expandable panel — pushes content down */}
      {open && (
        <div className="mt-1 rounded-[var(--radius-lg)] border border-[var(--color-border-dark)] bg-[var(--color-bg-card)] overflow-hidden">
          {/* Profile info + photo preview */}
          <div className="px-4 py-3 border-b border-[var(--color-border-dark)] flex items-center gap-3">
            {currentPhotoUrl ? (
              <img
                src={currentPhotoUrl}
                alt={displayName}
                className="w-10 h-10 rounded-full object-cover shrink-0"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-[var(--color-brand-pink)]/20 text-[var(--color-brand-pink)] flex items-center justify-center text-sm font-bold shrink-0">
                {getInitials(displayName || email)}
              </div>
            )}
            <div className="min-w-0">
              <p className="text-[13px] font-semibold text-[var(--color-text-primary)] truncate">
                {displayName}
              </p>
              <p className="text-[12px] text-[var(--color-text-muted)] truncate">{email}</p>
            </div>
          </div>

          {/* Change photo */}
          <div className="px-4 py-2.5 border-b border-[var(--color-border-dark)]">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handlePhotoUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-2 w-full text-[13px] text-[var(--color-text-secondary)] hover:text-[var(--color-brand-pink)] transition-colors disabled:opacity-50"
            >
              <IconCamera size={16} stroke={1.5} />
              <span>{uploading ? "Uploading…" : "Change Photo"}</span>
            </button>
          </div>

          {/* Theme toggle */}
          <div className="px-4 py-2.5 border-b border-[var(--color-border-dark)]">
            <button
              onClick={handleToggleTheme}
              className="flex items-center gap-2 w-full text-[13px] text-[var(--color-text-secondary)] hover:text-[var(--color-brand-pink)] transition-colors"
            >
              {mounted && (theme === "dark" ? <IconSun size={16} stroke={1.5} /> : <IconMoon size={16} stroke={1.5} />)}
              <span>{t("theme.toggle")}</span>
            </button>
          </div>

          {/* Language selector */}
          <div className="px-4 py-2.5 border-b border-[var(--color-border-dark)]">
            <div className="flex items-center gap-2 text-[13px] text-[var(--color-text-secondary)]">
              <IconLanguage size={16} stroke={1.5} />
              <span>{t("header.language") || "Language"}</span>
              <div className="ml-auto flex items-center gap-1 bg-[var(--color-bg-tertiary)] rounded-full p-0.5">
                {(["en", "nl"] as Locale[]).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setLocale(lang)}
                    className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold transition-colors ${
                      locale === lang
                        ? "bg-[var(--color-brand-pink)] text-white"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                    }`}
                  >
                    {lang.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-[13px] text-[var(--color-text-secondary)] hover:text-[var(--color-brand-pink)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
          >
            <IconLogout size={16} stroke={1.5} />
            <span>{t("header.logout") || "Sign out"}</span>
          </button>
        </div>
      )}
    </div>
  );
}
