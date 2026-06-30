"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useLocaleSwitcher } from "@/lib/i18n/locale-context";
import { SUPPORTED_LOCALES, type Locale } from "@/lib/i18n/config";
import { useCloseOnEscape, useOutsideClick } from "@/lib/use-outside-click";

const LOCALE_FLAG: Record<Locale, string> = {
  az: "🇦🇿",
  ru: "🇷🇺",
  en: "🇬🇧",
};

export function LanguageSwitcher() {
  const t = useTranslations("language");
  const { locale, setLocale } = useLocaleSwitcher();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useOutsideClick(containerRef, () => setOpen(false));
  useCloseOnEscape(open, () => setOpen(false));

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t("switchLanguage")}
        className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-bg"
      >
        <span aria-hidden>{LOCALE_FLAG[locale]}</span>
        <span className="uppercase">{locale}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-text-secondary" aria-hidden>
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-10 mt-1 w-48 rounded-md border border-border bg-surface py-1 shadow-lg">
          <p className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-text-secondary">
            {t("switchLanguage")}
          </p>
          {SUPPORTED_LOCALES.map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => {
                setLocale(code);
                setOpen(false);
              }}
              className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-bg ${
                code === locale ? "font-semibold text-primary" : "text-text-primary"
              }`}
            >
              <span className="flex items-center gap-2">
                <span aria-hidden>{LOCALE_FLAG[code]}</span>
                {t(code)}
              </span>
              {code === locale && <span aria-hidden>✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
