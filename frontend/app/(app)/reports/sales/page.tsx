"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getSalesAnalytics } from "@/lib/api/reports";
import type { SalesAnalytics } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { CategoryBarChart, StatusBarList, TrendChart } from "@/components/ui/charts";
import { DateRangeFilter, defaultDateRangeValue, toReportFilterParams } from "@/components/date-range-filter";
import { ReportExportButtons } from "@/components/report-export-buttons";

const TREND_SERIES = [
  { key: "sent", label: "sent", colorHex: "#0E7C9D", colorClass: "fill-info" },
  { key: "accepted", label: "accepted", colorHex: "#1A8754", colorClass: "fill-success" },
  { key: "rejected", label: "rejected", colorHex: "#C0392B", colorClass: "fill-danger" },
];

export default function SalesAnalyticsPage() {
  const t = useTranslations("reports");
  const tSales = useTranslations("sales");

  const [range, setRange] = useState(defaultDateRangeValue());
  const [data, setData] = useState<SalesAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const filterParams = toReportFilterParams(range);

  useEffect(() => {
    setData(null);
    setError(null);
    getSalesAnalytics(filterParams)
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.period, range.dateFrom, range.dateTo]);

  const trendSeries = TREND_SERIES.map((s) => ({ ...s, label: tSales(s.label as any) }));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <DateRangeFilter value={range} onChange={setRange} />
        <ReportExportButtons reportType="sales" filterParams={filterParams} />
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
            <StatCard label={t("kpiTotalQuotes")} value={data.kpis.total_quotes} tone="neutral" />
            <StatCard label={t("kpiAcceptedQuotes")} value={data.kpis.accepted_quotes} tone="success" />
            <StatCard label={t("kpiWinRate")} value={`${data.kpis.win_rate}%`} tone="success" />
            <StatCard label={t("kpiAcceptedRevenue")} value={data.kpis.accepted_revenue} tone="primary" />
            <StatCard label={t("kpiAvgQuoteValue")} value={data.kpis.avg_quote_value} tone="info" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title={t("revenueByProjectType")} />
              <CategoryBarChart
                data={data.revenue_by_project_type.map((r) => ({
                  label: tSales(`projectType_${r.project_type}` as any),
                  value: parseFloat(r.revenue),
                }))}
              />
            </Card>
            <Card>
              <CardHeader title={t("topCustomers")} />
              <CategoryBarChart
                data={data.top_customers.map((r) => ({ label: r.customer_name, value: parseFloat(r.revenue) }))}
              />
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("quoteTrend")} />
              <TrendChart data={data.monthly_trend} series={trendSeries} />
            </Card>
            <Card>
              <CardHeader title={t("quotesByStatus")} />
              <StatusBarList
                data={data.quotes_by_status.map((r) => ({ label: tSales(r.status as any), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
