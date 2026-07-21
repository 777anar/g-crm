const BCP47_BY_LOCALE: Record<string, string> = { az: "az", ru: "ru", en: "en-US" };

/** Reads the same localStorage key lib/i18n/locale-context.tsx persists the
 * active locale under, so plain (non-React) formatting helpers render dates
 * in the language the user actually has selected instead of always English. */
export function activeDateLocale(): string {
  if (typeof window === "undefined") return "az";
  const stored = window.localStorage.getItem("g_erp_locale");
  return (stored && BCP47_BY_LOCALE[stored]) || "az";
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(activeDateLocale(), { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(activeDateLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Whole-number grouped formatting for KPI headline figures (revenue, profit,
 * counts) -- the backend returns these as raw Decimal strings with no
 * currency symbol (aggregates can span multiple order currencies), so this
 * only adds locale-aware thousands separators, never a currency prefix. */
export function formatNumber(value: number | string): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString(activeDateLocale(), { maximumFractionDigits: 0 });
}

/** Converts a UTC ISO datetime into the value a <input type="datetime-local">
 * expects (no timezone, interpreted by the browser as local time). */
export function toDatetimeLocalValue(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Converts a <input type="datetime-local"> value (local time, no timezone)
 * back into a UTC ISO string for the API. */
export function fromDatetimeLocalValue(value: string): string | undefined {
  if (!value) return undefined;
  return new Date(value).toISOString();
}
