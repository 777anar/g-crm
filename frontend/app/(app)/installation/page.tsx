"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listInstallationJobs, listNotifications } from "@/lib/api/installation";
import type { InstallationJob, InstallationNotification } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { InstallationJobStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function daysFromNowIso(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function InstallationDashboardPage() {
  const t = useTranslations("installation");
  const router = useRouter();

  const [jobs, setJobs] = useState<InstallationJob[] | null>(null);
  const [notifications, setNotifications] = useState<InstallationNotification[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      listInstallationJobs({ limit: 200 }),
      listNotifications({ unreadOnly: true }),
    ])
      .then(([jobsRes, notifRes]) => {
        setJobs(jobsRes.items);
        setNotifications(notifRes.items);
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  const today = todayIso();
  const weekEnd = daysFromNowIso(7);

  const kpis = useMemo(() => {
    if (!jobs) return null;
    return {
      today: jobs.filter((j) => j.scheduled_date === today && j.status !== "cancelled").length,
      thisWeek: jobs.filter(
        (j) => j.scheduled_date && j.scheduled_date >= today && j.scheduled_date <= weekEnd && j.status !== "cancelled"
      ).length,
      inProgress: jobs.filter((j) => j.status === "in_progress" || j.status === "en_route").length,
      completed: jobs.filter((j) => j.status === "completed").length,
      unassigned: jobs.filter((j) => !j.crew_id && j.status !== "cancelled" && j.status !== "completed").length,
    };
  }, [jobs, today, weekEnd]);

  const upcoming = (jobs ?? [])
    .filter((j) => j.scheduled_date && j.scheduled_date >= today && j.status !== "cancelled" && j.status !== "completed")
    .sort((a, b) => (a.scheduled_date! < b.scheduled_date! ? -1 : 1))
    .slice(0, 8);

  const loading = jobs === null;

  return (
    <div className="flex flex-col gap-6">
      {error && <p className="text-sm text-danger">{error}</p>}

      {loading && !error && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <TableSkeleton rows={5} columns={4} />
        </div>
      )}

      {!loading && kpis && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard label={t("kpiToday")} value={kpis.today} tone="primary" />
            <StatCard label={t("kpiThisWeek")} value={kpis.thisWeek} tone="info" />
            <StatCard label={t("kpiInProgress")} value={kpis.inProgress} tone="warning" />
            <StatCard label={t("kpiCompleted")} value={kpis.completed} tone="success" />
            <StatCard label={t("kpiUnassigned")} value={kpis.unassigned} tone="danger" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("upcomingJobs")} />
              {upcoming.length === 0 ? (
                <EmptyState title={t("noUpcomingJobs")} />
              ) : (
                <div className="overflow-x-auto rounded-lg border border-border">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
                      <tr>
                        <th className="px-3 py-2 font-medium">{t("tableJob")}</th>
                        <th className="px-3 py-2 font-medium">{t("tableStatus")}</th>
                        <th className="px-3 py-2 font-medium">{t("tableScheduled")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {upcoming.map((job) => (
                        <tr
                          key={job.id}
                          onClick={() => router.push(`/installation/jobs/${job.id}`)}
                          className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                        >
                          <td className="px-3 py-2 font-mono font-medium text-text-primary">{job.job_number}</td>
                          <td className="px-3 py-2"><InstallationJobStatusBadge status={job.status} /></td>
                          <td className="px-3 py-2 text-text-secondary">
                            {job.scheduled_date ? formatDate(job.scheduled_date) : "—"}
                            {job.scheduled_time_slot ? ` · ${job.scheduled_time_slot}` : ""}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card>
              <CardHeader title={t("notifications")} />
              {!notifications || notifications.length === 0 ? (
                <p className="text-sm text-text-secondary">{t("noNotifications")}</p>
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {notifications.slice(0, 6).map((n) => (
                    <li key={n.id} className="py-2">
                      {n.installation_job_id ? (
                        <Link href={`/installation/jobs/${n.installation_job_id}`} className="text-sm font-medium text-primary hover:underline">
                          {n.title}
                        </Link>
                      ) : (
                        <p className="text-sm font-medium text-text-primary">{n.title}</p>
                      )}
                      <p className="text-xs text-text-secondary">{n.message}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
