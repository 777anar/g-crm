"use client";

import { useTranslations } from "next-intl";
import { useTheme } from "@/lib/theme/theme-context";

export function ThemeToggle() {
  const t = useTranslations("common");
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? t("switchToLightMode") : t("switchToDarkMode")}
      title={isDark ? t("switchToLightMode") : t("switchToDarkMode")}
      className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-surface text-text-secondary hover:bg-bg hover:text-text-primary"
    >
      {isDark ? (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path
            d="M8 1.5v1.5M8 13v1.5M3.05 3.05l1.06 1.06M11.9 11.9l1.06 1.06M1.5 8H3M13 8h1.5M3.05 12.95l1.06-1.06M11.9 4.11l1.06-1.06"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinecap="round"
          />
          <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path
            d="M13.5 9.5A6 6 0 016.5 2.5a6 6 0 106.99 7z"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  );
}
