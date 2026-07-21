"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getInventoryAnalytics } from "@/lib/api/reports";
import type { InventoryAnalytics } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { CategoryBarChart, StatusBarList } from "@/components/ui/charts";
import { ReportExportButtons } from "@/components/report-export-buttons";
import { useSlabStatusLabel } from "@/lib/i18n/hooks";

// Unlike every other Reports tab, Inventory has no DateRangeFilter: stock
// status is a live snapshot (a slab doesn't stop being "available" because
// it was received outside a report window), not a date-ranged aggregate --
// see InventoryAnalyticsUseCase's docstring on the backend for why. Export
// still works (period/date params only shape the export filename here).
export default function InventoryAnalyticsPage() {
  const t = useTranslations("reports");
  const slabStatusLabel = useSlabStatusLabel();

  const [data, setData] = useState<InventoryAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInventoryAnalytics()
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-text-secondary">{t("inventorySnapshotLabel")}</p>
        <ReportExportButtons reportType="inventory" filterParams={{}} />
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
            <StatCard label={t("kpiAvailableSlabs")} value={data.kpis.available_slabs} tone="success" />
            <StatCard label={t("kpiAvailableArea")} value={`${data.kpis.available_area_m2} m²`} tone="primary" />
            <StatCard label={t("kpiTotalSlabs")} value={data.kpis.total_slabs} tone="neutral" />
            <StatCard label={t("kpiReservedSlabs")} value={data.kpis.reserved_slabs} tone="info" />
            <StatCard label={t("kpiInProductionSlabs")} value={data.kpis.in_production_slabs} tone="warning" />
            <StatCard label={t("kpiMaterialsTracked")} value={data.kpis.materials_tracked} tone="neutral" />
            <StatCard label={t("kpiMaterialsOutOfStock")} value={data.kpis.materials_out_of_stock} tone="danger" />
            <StatCard label={t("kpiWarehousesCount")} value={data.kpis.warehouses_count} tone="neutral" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("availableStockByWarehouse")} />
              <CategoryBarChart
                data={data.available_slabs_by_warehouse.map((r) => ({ label: r.warehouse, value: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
            <Card>
              <CardHeader title={t("slabsByStatus")} />
              <StatusBarList
                data={data.slabs_by_status.map((r) => ({ label: slabStatusLabel(r.status), count: r.count }))}
                emptyLabel={t("noDataPeriod")}
              />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
