"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { getInventoryAnalytics, getLowStockSuggestions } from "@/lib/api/reports";
import type { InventoryAnalytics, LowStockSuggestions } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCard } from "@/components/ui/stat-card";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { CategoryBarChart, StatusBarList } from "@/components/ui/charts";
import { ReportExportButtons } from "@/components/report-export-buttons";
import { useSlabStatusLabel } from "@/lib/i18n/hooks";
import { usePermission } from "@/lib/permissions";

// Unlike every other Reports tab, Inventory has no DateRangeFilter: stock
// status is a live snapshot (a slab doesn't stop being "available" because
// it was received outside a report window), not a date-ranged aggregate --
// see InventoryAnalyticsUseCase's docstring on the backend for why. Export
// still works (period/date params only shape the export filename here).
export default function InventoryAnalyticsPage() {
  const t = useTranslations("reports");
  const slabStatusLabel = useSlabStatusLabel();
  const canCreatePurchaseOrder = usePermission("purchasing:purchase_orders:write");

  const [data, setData] = useState<InventoryAnalytics | null>(null);
  const [lowStock, setLowStock] = useState<LowStockSuggestions | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInventoryAnalytics()
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    getLowStockSuggestions()
      .then(setLowStock)
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

          <Card>
            <CardHeader title={t("lowStockTitle")} />
            <p className="mb-3 text-sm text-text-secondary">{t("lowStockDesc")}</p>
            {!lowStock && <TableSkeleton rows={3} columns={4} />}
            {lowStock && lowStock.materials.length === 0 && (
              <EmptyState title={t("lowStockEmpty")} description={t("lowStockEmptyDesc")} />
            )}
            {lowStock && lowStock.materials.length > 0 && (
              <table className="w-full text-left text-sm">
                <thead className="text-text-secondary">
                  <tr>
                    <th className="px-2 py-1 font-medium">{t("lowStockMaterial")}</th>
                    <th className="px-2 py-1 font-medium">{t("lowStockAvailableSlabs")}</th>
                    <th className="px-2 py-1 font-medium">{t("lowStockAvailableArea")}</th>
                    <th className="px-2 py-1 font-medium">{t("lowStockNoFitCount")}</th>
                    <th className="px-2 py-1 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {lowStock.materials.map((m) => (
                    <tr key={m.material_id} className="border-t border-border">
                      <td className="px-2 py-1 text-text-primary">
                        {m.brand_name} — {m.material_name}
                      </td>
                      <td className="px-2 py-1 text-text-secondary">{m.available_slab_count}</td>
                      <td className="px-2 py-1 text-text-secondary">{m.available_area_m2} m²</td>
                      <td className="px-2 py-1">
                        {m.no_fit_recommendation_count > 0 ? (
                          <Badge tone="warning">{m.no_fit_recommendation_count}</Badge>
                        ) : (
                          <span className="text-text-secondary">{m.no_fit_recommendation_count}</span>
                        )}
                      </td>
                      <td className="px-2 py-1 text-right">
                        {canCreatePurchaseOrder && (
                          <Link
                            href={`/purchasing/orders/new?material_id=${m.material_id}&description=${encodeURIComponent(`${m.brand_name} — ${m.material_name}`)}`}
                            className="text-primary hover:underline"
                          >
                            {t("lowStockCreatePo")}
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
