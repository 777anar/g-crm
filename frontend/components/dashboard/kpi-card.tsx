import { Card } from "@/components/ui/card";

export type KpiTone = "neutral" | "primary" | "success" | "warning" | "danger" | "info";

const TONE_DOT: Record<KpiTone, string> = {
  neutral: "bg-text-secondary",
  primary: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
};

/** A large executive-summary KPI tile -- deliberately separate from the
 * generic `StatCard` (used across every module's list views) so this one can
 * carry a bigger headline scale and an optional delta pill without changing
 * `StatCard`'s appearance everywhere else it's used. */
export function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
  delta,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: KpiTone;
  delta?: { pct: number; label: string } | null;
}) {
  return (
    <Card className="p-6 transition-shadow hover:shadow-elevated">
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${TONE_DOT[tone]}`} aria-hidden />
        <p className="text-sm font-medium text-text-secondary">{label}</p>
      </div>
      <p className="mt-3 text-3xl font-semibold tabular-nums text-text-primary">{value}</p>
      {(delta || hint) && (
        <div className="mt-2 flex items-center gap-2 text-xs">
          {delta && (
            <span
              className={`inline-flex items-center gap-1 font-medium ${delta.pct >= 0 ? "text-success" : "text-danger"}`}
              title={delta.label}
            >
              <span aria-hidden>{delta.pct >= 0 ? "▲" : "▼"}</span>
              {Math.abs(delta.pct).toFixed(1)}%
            </span>
          )}
          {hint && <span className="text-text-secondary">{hint}</span>}
        </div>
      )}
    </Card>
  );
}
