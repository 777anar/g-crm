"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getFinanceAnalytics } from "@/lib/api/reports";
import type { FinanceAnalytics } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { CategoryBarChart, TrendChart, TREND_COLORS } from "@/components/ui/charts";
import { DateRangeFilter, defaultDateRangeValue, toReportFilterParams } from "@/components/date-range-filter";
import { ReportExportButtons } from "@/components/report-export-buttons";

export default function FinanceAnalyticsPage() {
  const t = useTranslations("reports");

  const [range, setRange] = useState(defaultDateRangeValue());
  const [data, setData] = useState<FinanceAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const filterParams = toReportFilterParams(range);

  useEffect(() => {
    setData(null);
    setError(null);
    getFinanceAnalytics(filterParams)
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.period, range.dateFrom, range.dateTo]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <DateRangeFilter value={range} onChange={setRange} />
        <ReportExportButtons reportType="finance" filterParams={filterParams} />
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
            <StatCard label={t("kpiRevenue")} value={data.kpis.revenue} tone="primary" />
            <StatCard label={t("kpiCost")} value={data.kpis.cost} tone="info" />
            <StatCard label={t("kpiProfit")} value={data.kpis.profit} hint={t("kpiMargin", { pct: data.kpis.profit_margin_pct })} tone="success" />
            <StatCard label={t("kpiOrdersCount")} value={data.kpis.orders_count} tone="neutral" />
            <StatCard label={t("kpiRecognizedRevenue")} value={data.kpis.recognized_revenue} tone="success" />
            <StatCard label={t("kpiPipelineValue")} value={data.kpis.pipeline_value} tone="warning" />
            <StatCard label={t("kpiCancelledValue")} value={data.kpis.cancelled_value} tone="danger" />
            <StatCard label={t("kpiPurchaseCost")} value={data.kpis.purchase_cost} tone="info" />
            <StatCard label={t("kpiSupplierPayments")} value={data.kpis.supplier_payments} tone="success" />
            <StatCard label={t("kpiSupplierPayables")} value={data.kpis.supplier_payables} tone="warning" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("financeTrend")} />
              <TrendChart
                data={data.monthly_trend}
                series={[
                  { key: "revenue", label: t("kpiRevenue"), ...TREND_COLORS.revenue },
                  { key: "cost", label: t("kpiCost"), ...TREND_COLORS.cost },
                  { key: "profit", label: t("kpiProfit"), ...TREND_COLORS.profit },
                ]}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
            <Card>
              <CardHeader title={t("revenueByCurrency")} />
              <CategoryBarChart
                data={data.revenue_by_currency.map((r) => ({ label: r.currency, value: parseFloat(r.revenue) }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
