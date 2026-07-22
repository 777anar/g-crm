"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getProductionAnalytics } from "@/lib/api/reports";
import type { ProductionAnalytics } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { StatusBarList } from "@/components/ui/charts";
import { DateRangeFilter, defaultDateRangeValue, toReportFilterParams } from "@/components/date-range-filter";
import { ReportExportButtons } from "@/components/report-export-buttons";

export default function ProductionAnalyticsPage() {
  const t = useTranslations("reports");
  const tOrders = useTranslations("orders");

  const [range, setRange] = useState(defaultDateRangeValue());
  const [data, setData] = useState<ProductionAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const filterParams = toReportFilterParams(range);

  useEffect(() => {
    setData(null);
    setError(null);
    getProductionAnalytics(filterParams)
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.period, range.dateFrom, range.dateTo]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <DateRangeFilter value={range} onChange={setRange} />
        <ReportExportButtons reportType="production" filterParams={filterParams} />
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {!data && !error && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <TableSkeleton rows={5} columns={3} />
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard label={t("kpiOrdersInProduction")} value={data.kpis.orders_in_production} tone="warning" />
            <StatCard label={t("kpiOrdersReady")} value={data.kpis.orders_ready} tone="info" />
            <StatCard label={t("kpiEnteredProduction")} value={data.kpis.orders_entered_production} tone="neutral" />
            <StatCard label={t("kpiCompletedProduction")} value={data.kpis.orders_completed_production} tone="success" />
            <StatCard
              label={t("kpiAvgProductionCycle")}
              value={data.kpis.avg_production_cycle_days !== null ? t("daysValue", { days: data.kpis.avg_production_cycle_days }) : "—"}
              tone="primary"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title={t("orderStatusBreakdown")} />
              <StatusBarList
                data={data.order_status_breakdown.map((r) => ({ label: tOrders(r.status as Parameters<typeof tOrders>[0]), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
            <Card>
              <CardHeader title={t("itemProductionStatus")} />
              <StatusBarList
                data={data.item_production_status.map((r) => ({ label: tOrders(`prodStatus_${r.status}` as Parameters<typeof tOrders>[0]), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
