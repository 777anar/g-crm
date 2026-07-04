"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getInstallationAnalytics } from "@/lib/api/reports";
import type { InstallationAnalytics } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { StatusBarList } from "@/components/ui/charts";
import { DateRangeFilter, defaultDateRangeValue, toReportFilterParams } from "@/components/date-range-filter";
import { ReportExportButtons } from "@/components/report-export-buttons";

export default function InstallationAnalyticsPage() {
  const t = useTranslations("reports");
  const tOrders = useTranslations("orders");

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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <TableSkeleton rows={5} columns={3} />
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label={t("kpiOrdersAwaitingInstallation")} value={data.kpis.orders_awaiting_installation} tone="warning" />
            <StatCard label={t("kpiOrdersInstalled")} value={data.kpis.orders_installed} tone="success" />
            <StatCard
              label={t("kpiAvgInstallationCycle")}
              value={data.kpis.avg_installation_cycle_days !== null ? t("daysValue", { days: data.kpis.avg_installation_cycle_days }) : "—"}
              tone="primary"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title={t("orderStatusBreakdown")} />
              <StatusBarList
                data={data.order_status_breakdown.map((r) => ({ label: tOrders(r.status as any), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
            <Card>
              <CardHeader title={t("itemInstallationStatus")} />
              <StatusBarList
                data={data.item_installation_status.map((r) => ({ label: tOrders(`instStatus_${r.status}` as any), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
