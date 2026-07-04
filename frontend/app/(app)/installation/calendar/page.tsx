"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listInstallationJobs } from "@/lib/api/installation";
import type { InstallationJob } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";

const WEEKDAY_KEYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"] as const;

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function isoDate(year: number, month: number, day: number): string {
  return `${year}-${pad2(month + 1)}-${pad2(day)}`;
}

/** A hand-built month grid -- no calendar library in this project (see the
 * custom SVG charts in components/ui/charts.tsx for the same tradeoff). */
export default function InstallationCalendarPage() {
  const t = useTranslations("installation");
  const router = useRouter();

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth()); // 0-indexed
  const [jobs, setJobs] = useState<InstallationJob[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const firstOfMonth = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const leadingBlanks = firstOfMonth.getDay();

  useEffect(() => {
    setJobs(null);
    listInstallationJobs({
      dateFrom: isoDate(year, month, 1),
      dateTo: isoDate(year, month, daysInMonth),
      limit: 200,
    })
      .then((r) => setJobs(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month]);

  const jobsByDay = useMemo(() => {
    const map: Record<string, InstallationJob[]> = {};
    for (const job of jobs ?? []) {
      if (!job.scheduled_date) continue;
      (map[job.scheduled_date] ??= []).push(job);
    }
    return map;
  }, [jobs]);

  function goToPrevMonth() {
    if (month === 0) { setYear(year - 1); setMonth(11); } else { setMonth(month - 1); }
  }
  function goToNextMonth() {
    if (month === 11) { setYear(year + 1); setMonth(0); } else { setMonth(month + 1); }
  }
  function goToToday() {
    setYear(now.getFullYear());
    setMonth(now.getMonth());
  }

  const monthLabel = firstOfMonth.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const cells: (number | null)[] = [
    ...Array.from({ length: leadingBlanks }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  const todayIso = now.toISOString().slice(0, 10);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">{monthLabel}</h2>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={goToPrevMonth}>←</Button>
          <Button variant="secondary" onClick={goToToday}>{t("today")}</Button>
          <Button variant="secondary" onClick={goToNextMonth}>→</Button>
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}
      {jobs === null && !error && <TableSkeleton rows={5} columns={7} />}

      {jobs !== null && (
        <div className="grid grid-cols-7 gap-px overflow-hidden rounded-lg border border-border bg-border">
          {WEEKDAY_KEYS.map((key) => (
            <div key={key} className="bg-bg px-2 py-1 text-center text-xs font-medium text-text-secondary">
              {t(`weekday_${key}`)}
            </div>
          ))}
          {cells.map((day, i) => {
            if (day === null) return <div key={`blank-${i}`} className="min-h-[6rem] bg-surface" />;
            const dateStr = isoDate(year, month, day);
            const dayJobs = jobsByDay[dateStr] ?? [];
            const isToday = dateStr === todayIso;
            return (
              <div key={dateStr} className="min-h-[6rem] bg-surface p-1.5">
                <p className={`mb-1 text-xs font-medium ${isToday ? "text-primary" : "text-text-secondary"}`}>
                  {day}
                </p>
                <div className="flex flex-col gap-1">
                  {dayJobs.slice(0, 3).map((job) => (
                    <button
                      key={job.id}
                      onClick={() => router.push(`/installation/jobs/${job.id}`)}
                      className={`truncate rounded px-1.5 py-0.5 text-left text-xs font-medium ${
                        job.status === "completed"
                          ? "bg-success/10 text-success"
                          : job.status === "cancelled"
                            ? "bg-danger/10 text-danger"
                            : "bg-primary/10 text-primary"
                      }`}
                      title={job.job_number}
                    >
                      {job.job_number}
                    </button>
                  ))}
                  {dayJobs.length > 3 && (
                    <span className="text-xs text-text-secondary">+{dayJobs.length - 3}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
