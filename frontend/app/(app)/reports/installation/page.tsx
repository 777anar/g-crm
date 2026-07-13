"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getInstallationAnalytics } from "@/lib/api/reports";
import type { InstallationAnalytics } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { CategoryBarChart, StatusBarList, TrendChart, TREND_COLORS } from "@/components/ui/charts";
import { DateRangeFilter, defaultDateRangeValue, toReportFilterParams } from "@/components/date-range-filter";
import { ReportExportButtons } from "@/components/report-export-buttons";

export default function InstallationAnalyticsPage() {
  const t = useTranslations("reports");
  const tInstallation = useTranslations("installation");

  const [range, setRange] = useState(defaultDateRangeValue());
  const [data, setData] = useState<InstallationAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const filterParams = toReportFilterParams(range);

  useEffect(() => {
    setData(null);
    setError(null);
    getInstallationAnalytics(filterParams)
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.period, range.dateFrom, range.dateTo]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <DateRangeFilter value={range} onChange={setRange} />
        <ReportExportButtons reportType="installation" filterParams={filterParams} />
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {!data && !error && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <TableSkeleton rows={5} columns={3} />
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
            <StatCard label={t("kpiJobsCreated")} value={data.kpis.jobs_created} tone="neutral" />
            <StatCard label={t("kpiJobsCompleted")} value={data.kpis.jobs_completed} tone="success" />
            <StatCard label={t("kpiJobsAwaiting")} value={data.kpis.jobs_awaiting} tone="warning" />
            <StatCard label={t("kpiJobsDelayed")} value={data.kpis.jobs_delayed} tone="danger" />
            <StatCard
              label={t("kpiAvgDelay")}
              value={data.kpis.avg_delay_days !== null ? t("daysValue", { days: data.kpis.avg_delay_days }) : "—"}
              tone="warning"
            />
            <StatCard
              label={t("kpiAvgInstallTime")}
              value={data.kpis.avg_installation_hours !== null ? t("hoursValue", { hours: data.kpis.avg_installation_hours }) : "—"}
              tone="primary"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("dailyInstallations")} />
              <TrendChart
                data={data.daily_installations.map((r) => ({ month: r.date, count: r.count }))}
                series={[{ key: "count", label: t("dailyInstallations"), ...TREND_COLORS.revenue }]}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
            <Card>
              <CardHeader title={t("jobStatusBreakdown")} />
              <StatusBarList
                data={data.job_status_breakdown.map((r) => ({ label: tInstallation(r.status as any), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
          </div>

          <Card>
            <CardHeader title={t("crewProductivity")} />
            {data.crew_productivity.length === 0 ? (
              <p className="text-sm text-text-secondary">{t("noDataPeriod")}</p>
            ) : (
              <CategoryBarChart
                data={data.crew_productivity.map((r) => ({ label: r.crew_name, value: r.completed_count }))}
              />
            )}
          </Card>
        </>
      )}
    </div>
  );
}
