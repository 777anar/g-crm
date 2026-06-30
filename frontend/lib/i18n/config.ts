import az from "@/locales/az.json";
import en from "@/locales/en.json";
import ru from "@/locales/ru.json";

export const SUPPORTED_LOCALES = ["az", "ru", "en"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "az";
export const FALLBACK_LOCALE: Locale = "en";

const RAW_MESSAGES: Record<Locale, Record<string, unknown>> = { az, ru, en };

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Deep-merges `override` onto `base`, so any key missing in a non-English
 * locale file silently falls back to the English string instead of
 * rendering blank or throwing -- satisfying "English (keep as fallback)". */
function deepMerge(base: Record<string, unknown>, override: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = { ...base };
  for (const key of Object.keys(override)) {
    const baseValue = base[key];
    const overrideValue = override[key];
    if (isPlainObject(baseValue) && isPlainObject(overrideValue)) {
      result[key] = deepMerge(baseValue, overrideValue);
    } else {
      result[key] = overrideValue;
    }
  }
  return result;
}

export function getMessagesForLocale(locale: Locale): Record<string, unknown> {
  const fallback = RAW_MESSAGES[FALLBACK_LOCALE];
  if (locale === FALLBACK_LOCALE) return fallback;
  return deepMerge(fallback, RAW_MESSAGES[locale]);
}

export function isSupportedLocale(value: string | null): value is Locale {
  return !!value && (SUPPORTED_LOCALES as readonly string[]).includes(value);
}
