"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getExecutiveDashboard } from "@/lib/api/reports";
import type { ExecutiveDashboard } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { StatusBarList, TrendChart, TREND_COLORS } from "@/components/ui/charts";
import { DateRangeFilter, defaultDateRangeValue, toReportFilterParams } from "@/components/date-range-filter";
import { ReportExportButtons } from "@/components/report-export-buttons";
import { useCustomerStatusLabel } from "@/lib/i18n/hooks";

export default function ExecutiveDashboardPage() {
  const t = useTranslations("reports");
  const tOrders = useTranslations("orders");
  const customerStatusLabel = useCustomerStatusLabel();

  const [range, setRange] = useState(defaultDateRangeValue());
  const [data, setData] = useState<ExecutiveDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const filterParams = toReportFilterParams(range);

  useEffect(() => {
    setData(null);
    setError(null);
    getExecutiveDashboard(filterParams)
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.period, range.dateFrom, range.dateTo]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <DateRangeFilter value={range} onChange={setRange} />
        <ReportExportButtons reportType="executive" filterParams={filterParams} />
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {!data && !error && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <TableSkeleton rows={5} columns={3} />
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label={t("kpiRevenue")} value={`${data.kpis.revenue}`} tone="primary" />
            <StatCard label={t("kpiProfit")} value={`${data.kpis.profit}`} hint={t("kpiMargin", { pct: data.kpis.profit_margin_pct })} tone="success" />
            <StatCard label={t("kpiActiveCustomers")} value={data.kpis.active_customers} tone="info" />
            <StatCard label={t("kpiOrdersCreated")} value={data.kpis.orders_created} tone="neutral" />
            <StatCard label={t("kpiQuoteWinRate")} value={`${data.kpis.quote_win_rate}%`} tone="success" />
            <StatCard label={t("kpiLeadConversion")} value={`${data.kpis.lead_conversion_rate}%`} tone="info" />
            <StatCard label={t("kpiOrdersInProduction")} value={data.kpis.orders_in_production} tone="warning" />
            <StatCard label={t("kpiOrdersAwaitingInstallation")} value={data.kpis.orders_awaiting_installation} tone="warning" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("revenueTrend")} />
              <TrendChart
                data={data.revenue_trend.map((r) => ({ month: r.month, revenue: r.revenue, profit: r.profit }))}
                series={[
                  { key: "revenue", label: t("kpiRevenue"), ...TREND_COLORS.revenue },
                  { key: "profit", label: t("kpiProfit"), ...TREND_COLORS.profit },
                ]}
              />
            </Card>

            <Card>
              <CardHeader title={t("customersByStatus")} />
              <StatusBarList
                data={data.customers_by_status.map((r) => ({ label: customerStatusLabel(r.status), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
          </div>

          <Card>
            <CardHeader title={t("ordersByStatus")} />
            <StatusBarList
              data={data.orders_by_status.map((r) => ({ label: tOrders(r.status as any), count: r.count }))}
              emptyLabel={t("noDataPeriod")}
            />
          </Card>
        </>
      )}
    </div>
  );
}
