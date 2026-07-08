"use client";

import { useId, useMemo, useState } from "react";

/** The app's semantic tones, validated as a categorical palette (fixed order,
 * CVD-safe adjacent pairs) -- see UI_UX_GUIDELINES.md / tailwind.config.ts.
 * Never reassign or cycle this order; a chart with more series than colors
 * folds the remainder into "Other" instead of repeating a hue. */
const CATEGORICAL_CLASS = ["fill-primary", "fill-info", "fill-success", "fill-warning", "fill-danger"] as const;

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
  const steps = [1, 2, 2.5, 5, 10];
  for (const step of steps) {
    const candidate = step * magnitude;
    if (candidate >= value) return candidate;
  }
  return 10 * magnitude;
}

function compactNumber(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

// ── Status / ordinal bar list ─────────────────────────────────────────────────
// Order/customer/quote status is a pipeline sequence -- swapping the category
// order would change its meaning, so this is ordinal (one hue, magnitude by
// bar width), not categorical. Shared by Dashboard and every Reports screen
// so the "list of status bars" idiom isn't reimplemented per page.

export function StatusBarList({
  data,
  emptyLabel,
}: {
  data: { label: string; count: number }[];
  emptyLabel?: string;
}) {
  const max = Math.max(...data.map((d) => d.count), 1);
  const visible = data.filter((d) => d.count > 0);

  if (visible.length === 0) {
    return <p className="text-sm text-text-secondary">{emptyLabel ?? "—"}</p>;
  }

  return (
    <ul className="flex flex-col gap-3">
      {visible.map(({ label, count }) => {
        const pct = Math.round((count / max) * 100);
        return (
          <li key={label}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-text-primary">{label}</span>
              <span className="tabular-nums text-text-secondary">{count}</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-bg">
              <div className="h-1.5 rounded-full bg-primary" style={{ width: `${pct}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

// ── Categorical bar chart (revenue by project type, top customers, ...) ──────

export function CategoryBarChart({
  data,
  height = 200,
  valueFormatter = compactNumber,
}: {
  data: { label: string; value: number }[];
  height?: number;
  valueFormatter?: (value: number) => string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = niceMax(Math.max(...data.map((d) => d.value), 0));
  const barSlot = 100 / Math.max(data.length, 1);
  const barWidth = Math.min(barSlot * 0.6, 20);

  if (data.length === 0) {
    return <p className="text-sm text-text-secondary">No data for this period.</p>;
  }

  return (
    <div className="relative">
      {/* SVG holds only geometric marks -- viewBox with preserveAspectRatio="none"
       * scales non-uniformly, which would stretch <text> glyphs into illegible
       * shapes, so labels live in the HTML row below instead. */}
      <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="w-full" style={{ height }}>
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <line key={f} x1={0} x2={100} y1={height - f * height} y2={height - f * height} stroke="var(--color-border)" strokeWidth={0.5} />
        ))}
        {data.map((d, i) => {
          const barHeight = max > 0 ? (d.value / max) * height : 0;
          const x = i * barSlot + (barSlot - barWidth) / 2;
          const y = height - barHeight;
          const colorClass = CATEGORICAL_CLASS[i % CATEGORICAL_CLASS.length];
          return (
            <g key={d.label} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <rect x={x} y={y} width={barWidth} height={Math.max(barHeight, 1)} rx={1.5} className={`${colorClass} ${hover === i ? "opacity-90" : ""}`} />
              <rect x={x - 2} y={0} width={barWidth + 4} height={height} fill="transparent" />
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex">
        {data.map((d) => (
          <div key={d.label} className="truncate px-0.5 text-center text-xs text-text-secondary" style={{ width: `${barSlot}%` }}>
            {d.label}
          </div>
        ))}
      </div>
      {hover !== null && (
        <div
          className="pointer-events-none absolute -translate-x-1/2 -translate-y-full rounded-md border border-border bg-surface px-2 py-1 text-xs shadow-sm"
          style={{ left: `${hover * barSlot + barSlot / 2}%`, top: 8 }}
        >
          <p className="font-medium text-text-primary">{valueFormatter(data[hover].value)}</p>
          <p className="text-text-secondary">{data[hover].label}</p>
        </div>
      )}
    </div>
  );
}

// ── Trend line chart (revenue / profit / cost over time) ─────────────────────

export type TrendSeries = { key: string; label: string; colorHex: string; colorClass: string };

export function TrendChart({
  data,
  series,
  height = 240,
  valueFormatter = compactNumber,
}: {
  data: Record<string, number | string>[];
  series: TrendSeries[];
  height?: number;
  valueFormatter?: (value: number) => string;
}) {
  const clipId = useId();
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const max = useMemo(
    () => niceMax(Math.max(...data.flatMap((d) => series.map((s) => Number(d[s.key]) || 0)), 0)),
    [data, series]
  );

  if (data.length === 0) {
    return <p className="text-sm text-text-secondary">No data for this period.</p>;
  }

  const plotH = height - 24;
  const stepX = data.length > 1 ? 100 / (data.length - 1) : 0;
  const xFor = (i: number) => (data.length > 1 ? i * stepX : 50);
  const yFor = (v: number) => plotH - (max > 0 ? (v / max) * plotH : 0);

  return (
    <div className="relative">
      {series.length > 1 && (
        <div className="mb-2 flex flex-wrap gap-4 text-xs text-text-secondary">
          {series.map((s) => (
            <span key={s.key} className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 rounded-full" style={{ backgroundColor: s.colorHex }} />
              {s.label}
            </span>
          ))}
        </div>
      )}
      {/* SVG holds only geometric marks -- see CategoryBarChart for why text
       * labels are never placed inside a non-uniformly scaled viewBox. */}
      <svg viewBox={`0 0 100 ${plotH}`} preserveAspectRatio="none" className="w-full" style={{ height: plotH }}>
        <defs>
          <clipPath id={clipId}>
            <rect x={0} y={0} width={100} height={plotH} />
          </clipPath>
        </defs>
        {[0, 0.5, 1].map((f) => (
          <line key={f} x1={0} x2={100} y1={plotH * (1 - f)} y2={plotH * (1 - f)} stroke="var(--color-border)" strokeWidth={0.5} />
        ))}
        {series.map((s) => {
          const points = data.map((d, i) => `${xFor(i)},${yFor(Number(d[s.key]) || 0)}`).join(" ");
          return (
            <g key={s.key} clipPath={`url(#${clipId})`}>
              <polyline points={points} fill="none" stroke={s.colorHex} strokeWidth={0.8} strokeLinejoin="round" strokeLinecap="round" />
              {data.map((d, i) => (
                <circle
                  key={i}
                  cx={xFor(i)}
                  cy={yFor(Number(d[s.key]) || 0)}
                  r={hoverIndex === i ? 1.6 : 1.1}
                  fill={s.colorHex}
                  stroke="var(--color-surface)"
                  strokeWidth={0.6}
                />
              ))}
            </g>
          );
        })}
        {hoverIndex !== null && (
          <line x1={xFor(hoverIndex)} x2={xFor(hoverIndex)} y1={0} y2={plotH} stroke="#5B6270" strokeWidth={0.3} />
        )}
        {data.map((_, i) => (
          <rect
            key={i}
            x={xFor(i) - stepX / 2}
            y={0}
            width={stepX || 100}
            height={plotH}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(i)}
            onMouseLeave={() => setHoverIndex(null)}
          />
        ))}
      </svg>
      <div className="relative mt-1 h-4 text-xs text-text-secondary">
        {data.map((d, i) => (
          <span key={i} className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: `${xFor(i)}%` }}>
            {String(d.month ?? d.label ?? "")}
          </span>
        ))}
      </div>
      {hoverIndex !== null && (
        <div
          className="pointer-events-none absolute -translate-x-1/2 rounded-md border border-border bg-surface px-2 py-1.5 text-xs shadow-sm"
          style={{ left: `${xFor(hoverIndex)}%`, top: 0 }}
        >
          <p className="mb-0.5 font-medium text-text-primary">{String(data[hoverIndex].month ?? "")}</p>
          {series.map((s) => (
            <p key={s.key} className="flex items-center gap-1.5 text-text-secondary">
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: s.colorHex }} />
              {s.label}: <span className="font-medium text-text-primary">{valueFormatter(Number(data[hoverIndex!][s.key]) || 0)}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export const TREND_COLORS = {
  revenue: { colorHex: "#1F4FD8", colorClass: "fill-primary" },
  profit: { colorHex: "#1A8754", colorClass: "fill-success" },
  cost: { colorHex: "#0E7C9D", colorClass: "fill-info" },
};
