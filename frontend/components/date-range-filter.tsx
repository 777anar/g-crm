"use client";

import { useTranslations } from "next-intl";
import type { ReportPeriod } from "@/lib/types";

export type DateRangeValue = {
  period: ReportPeriod;
  dateFrom: string;
  dateTo: string;
};

const PRESETS: ReportPeriod[] = ["7d", "30d", "90d", "12m"];

/** One filter row, above the charts it scopes -- per dataviz interaction
 * conventions: presets before a custom range, and every chart/stat on the
 * page re-renders against the same date slice so the numbers always agree. */
export function DateRangeFilter({
  value,
  onChange,
}: {
  value: DateRangeValue;
  onChange: (next: DateRangeValue) => void;
}) {
  const t = useTranslations("reports");

  return (
    <div className="flex flex-wrap items-center gap-2">
      {PRESETS.map((preset) => (
        <button
          key={preset}
          type="button"
          onClick={() => onChange({ ...value, period: preset })}
          className={`rounded-md px-3 py-1.5 text-sm font-medium ${
            value.period === preset
              ? "bg-primary text-white"
              : "border border-border bg-surface text-text-primary hover:bg-bg"
          }`}
        >
          {t(`period_${preset}` as Parameters<typeof t>[0])}
        </button>
      ))}

      <div className="flex items-center gap-2">
        <input
          type="date"
          value={value.dateFrom}
          onChange={(e) => onChange({ ...value, period: "custom", dateFrom: e.target.value })}
          className="rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        />
        <span className="text-sm text-text-secondary">{t("dateRangeTo")}</span>
        <input
          type="date"
          value={value.dateTo}
          onChange={(e) => onChange({ ...value, period: "custom", dateTo: e.target.value })}
          className="rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        />
      </div>
    </div>
  );
}

/** A preset sends just `period` (the backend resolves the rolling window);
 * "custom" sends the explicit from/to pair -- see resolve_date_range() in
 * backend/modules/reports/domain/value_objects.py. */
export function toReportFilterParams(value: DateRangeValue) {
  if (value.period === "custom") {
    return { period: value.period, dateFrom: value.dateFrom, dateTo: value.dateTo };
  }
  return { period: value.period };
}

export function defaultDateRangeValue(): DateRangeValue {
  const today = new Date();
  const from = new Date(today);
  from.setDate(from.getDate() - 30);
  return {
    period: "30d",
    dateFrom: from.toISOString().slice(0, 10),
    dateTo: today.toISOString().slice(0, 10),
  };
}
