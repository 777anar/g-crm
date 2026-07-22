"use client";

import { useTranslations } from "next-intl";
import { Moon, Sun } from "lucide-react";
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
      {isDark ? <Sun size={16} strokeWidth={1.3} aria-hidden /> : <Moon size={16} strokeWidth={1.3} aria-hidden />}
    </button>
  );
}
