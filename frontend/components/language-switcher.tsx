"use client";

import { useTranslations } from "next-intl";
import { useLocaleSwitcher } from "@/lib/i18n/locale-context";
import { SUPPORTED_LOCALES, type Locale } from "@/lib/i18n/config";
import { DropdownItem, DropdownPanel, useDropdown } from "@/components/ui/dropdown";

const LOCALE_FLAG: Record<Locale, string> = {
  az: "🇦🇿",
  ru: "🇷🇺",
  en: "🇬🇧",
};

export function LanguageSwitcher() {
  const t = useTranslations("language");
  const { locale, setLocale } = useLocaleSwitcher();
  const { open, containerRef, toggle, close } = useDropdown();

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={toggle}
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
        <DropdownPanel align="right" widthClassName="w-48" label={t("switchLanguage")}>
          {SUPPORTED_LOCALES.map((code) => (
            <DropdownItem
              key={code}
              active={code === locale}
              onClick={() => {
                setLocale(code);
                close();
              }}
            >
              <span className="flex items-center gap-2">
                <span aria-hidden>{LOCALE_FLAG[code]}</span>
                {t(code)}
              </span>
            </DropdownItem>
          ))}
        </DropdownPanel>
      )}
    </div>
  );
}
