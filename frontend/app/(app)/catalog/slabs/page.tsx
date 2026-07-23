"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { createSlab, listMaterials, listSlabs, listWarehouses, reserveSlab, updateSlabStatus } from "@/lib/api/catalog";
import { SLAB_STATUSES, type Material, type Slab, type SlabStatus, type Warehouse } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SlabStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SelectField, TextField } from "@/components/ui/field";
import { SortableHeader } from "@/components/ui/sortable-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { useSlabStatusLabel } from "@/lib/i18n/hooks";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { usePermission } from "@/lib/permissions";
import { useToast } from "@/components/ui/toast";

export default function SlabsPage() {
  const t = useTranslations("catalog");
  const tCommon = useTranslations("common");
  const statusLabel = useSlabStatusLabel();
  const canWrite = usePermission("catalog:slabs:write");
  const toast = useToast();

  const [slabs, setSlabs] = useState<Slab[] | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [materialFilter, setMaterialFilter] = useState("");
  const [warehouseFilter, setWarehouseFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<SlabStatus | "">("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [error, setError] = useState<string | null>(null);
  const [changingId, setChangingId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [reserveOrderId, setReserveOrderId] = useState("");
  const [reserveOrderItemId, setReserveOrderItemId] = useState("");
  const [reserving, setReserving] = useState(false);

  const [materialId, setMaterialId] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [slabNumber, setSlabNumber] = useState("");
  const [lengthMm, setLengthMm] = useState("");
  const [widthMm, setWidthMm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listMaterials({ limit: 100 }).then((res) => {
      setMaterials(res.items);
      if (res.items.length > 0) setMaterialId((current) => current || res.items[0].id);
    }).catch(() => {});
    listWarehouses().then((res) => {
      setWarehouses(res.items);
      if (res.items.length > 0) setWarehouseId((current) => current || res.items[0].id);
    }).catch(() => {});
  }, []);

  const reload = useCallback(async () => {
    try {
      const res = await listSlabs({
        materialId: materialFilter || undefined,
        warehouseId: warehouseFilter || undefined,
        status: statusFilter || undefined,
        search,
        sort,
      });
      setSlabs(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }, [materialFilter, warehouseFilter, statusFilter, search, sort, t]);

  useEffect(() => {
    setSlabs(null);
    reload();
  }, [reload]);

  function materialName(id: string) {
    return materials.find((m) => m.id === id)?.name ?? tCommon("dash");
  }

  function warehouseName(id: string) {
    return warehouses.find((w) => w.id === id)?.name ?? tCommon("dash");
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createSlab({
        material_id: materialId,
        warehouse_id: warehouseId,
        slab_number: slabNumber,
        length_mm: lengthMm || undefined,
        width_mm: widthMm || undefined,
        weight_kg: weightKg || undefined,
      });
      setSlabNumber("");
      setLengthMm("");
      setWidthMm("");
      setWeightKg("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStatusChange(slabId: string, status: SlabStatus) {
    setChangingId(slabId);
    setError(null);
    try {
      await updateSlabStatus(slabId, status);
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("updateFailed"));
    } finally {
      setChangingId(null);
    }
  }

  const availableSlabs = (slabs ?? []).filter((s) => s.status === "available");

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAllAvailable() {
    setSelected((prev) =>
      prev.size === availableSlabs.length ? new Set() : new Set(availableSlabs.map((s) => s.id))
    );
  }

  async function handleBulkReserve() {
    const ids = Array.from(selected);
    if (ids.length === 0 || !reserveOrderId || !reserveOrderItemId) return;
    setReserving(true);
    try {
      const results = await Promise.allSettled(
        ids.map((id) => reserveSlab(id, { order_id: reserveOrderId, order_item_id: reserveOrderItemId }))
      );
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed > 0) {
        toast.error(t("bulkReservePartialFailure", { succeeded: ids.length - failed, count: ids.length }));
      } else {
        toast.success(t("bulkReserveSucceeded", { count: ids.length }));
      }
      setSelected(new Set());
      setReserveOrderId("");
      setReserveOrderItemId("");
      await reload();
    } finally {
      setReserving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("slabsTitle")}</h1>
          <p className="text-sm text-text-secondary">{t("slabsSubtitle")}</p>
        </div>
        <Link href="/catalog/reservations" className="text-sm text-primary hover:underline">
          {t("viewReservations")} →
        </Link>
      </div>

      {canWrite && (
      <Card>
        <CardHeader title={t("createSlab")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-3" onSubmit={handleCreate}>
          <SelectField label={t("material")} value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </SelectField>
          <SelectField label={t("warehouse")} value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} required>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t("slabNumber")}
            value={slabNumber}
            onChange={(e) => setSlabNumber(e.target.value)}
            required
          />
          <TextField label={t("lengthMm")} value={lengthMm} onChange={(e) => setLengthMm(e.target.value)} />
          <TextField label={t("widthMm")} value={widthMm} onChange={(e) => setWidthMm(e.target.value)} />
          <TextField label={t("weightKg")} value={weightKg} onChange={(e) => setWeightKg(e.target.value)} />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !slabNumber || !materialId || !warehouseId}>
              {submitting ? t("creating") : t("createSlab")}
            </Button>
          </div>
        </form>
      </Card>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <input
          ref={searchInputRef}
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={t("searchSlabsPlaceholder")}
          className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        />
        <div className="flex items-center gap-2">
          <label htmlFor="slab-material-filter" className="text-sm text-text-secondary">
            {t("material")}
          </label>
          <select
            id="slab-material-filter"
            value={materialFilter}
            onChange={(e) => setMaterialFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{tCommon("dash")}</option>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="slab-warehouse-filter" className="text-sm text-text-secondary">
            {t("filterByWarehouse")}
          </label>
          <select
            id="slab-warehouse-filter"
            value={warehouseFilter}
            onChange={(e) => setWarehouseFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{t("allWarehouses")}</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="slab-status-filter" className="text-sm text-text-secondary">
            {t("filterByStatus")}
          </label>
          <select
            id="slab-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as SlabStatus | "")}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{t("allStatuses")}</option>
            {SLAB_STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {canWrite && selected.size > 0 && (
        <Card className="border-primary/30 bg-primary/5">
          <div className="flex flex-wrap items-end gap-3">
            <p className="text-sm font-medium text-text-primary">
              {t("bulkReserveSelected", { count: selected.size })}
            </p>
            <TextField label={t("orderId")} value={reserveOrderId} onChange={(e) => setReserveOrderId(e.target.value)} />
            <TextField
              label={t("orderItemId")}
              value={reserveOrderItemId}
              onChange={(e) => setReserveOrderItemId(e.target.value)}
            />
            <Button
              loading={reserving}
              disabled={!reserveOrderId || !reserveOrderItemId}
              onClick={handleBulkReserve}
            >
              {t("reserveSelected")}
            </Button>
            <Button variant="secondary" onClick={() => setSelected(new Set())}>
              {tCommon("cancel")}
            </Button>
          </div>
        </Card>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {slabs === null && !error && <TableSkeleton rows={5} columns={6} />}

      {slabs && slabs.length === 0 && <EmptyState title={t("noSlabsYet")} description={t("noSlabsDesc")} />}

      {slabs && slabs.length > 0 && (
        <div className={tableScrollShellClass}>
          <table className="w-full text-left text-sm">
            <thead className={stickyTheadClass}>
              <tr>
                {canWrite && (
                  <th className="px-4 py-2">
                    <input
                      type="checkbox"
                      aria-label={t("selectAllAvailable")}
                      checked={selected.size > 0 && selected.size === availableSlabs.length}
                      onChange={toggleSelectAllAvailable}
                    />
                  </th>
                )}
                <SortableHeader field="slab_number" label={t("tableSlabNumber")} sort={sort} onSortChange={setSort} />
                <th className="px-4 py-2 font-medium">{t("tableMaterial")}</th>
                <th className="px-4 py-2 font-medium">{t("tableWarehouse")}</th>
                <SortableHeader field="area_m2" label={t("tableArea")} sort={sort} onSortChange={setSort} />
                <th className="px-4 py-2 font-medium">{t("tableWeight")}</th>
                <th className="px-4 py-2 font-medium">{t("changeStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {slabs.map((slab) => (
                <tr key={slab.id} className="border-b border-border last:border-0 hover:bg-bg">
                  {canWrite && (
                    <td className="px-4 py-2">
                      {slab.status === "available" && (
                        <input
                          type="checkbox"
                          aria-label={t("selectSlab", { number: slab.slab_number })}
                          checked={selected.has(slab.id)}
                          onChange={() => toggleSelect(slab.id)}
                        />
                      )}
                    </td>
                  )}
                  <td className="px-4 py-2 font-medium text-text-primary">{slab.slab_number}</td>
                  <td className="px-4 py-2 text-text-secondary">{materialName(slab.material_id)}</td>
                  <td className="px-4 py-2 text-text-secondary">{warehouseName(slab.warehouse_id)}</td>
                  <td className="px-4 py-2 text-text-secondary">{slab.area_m2 ?? tCommon("dash")}</td>
                  <td className="px-4 py-2 text-text-secondary">{slab.weight_kg ?? tCommon("dash")}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <SlabStatusBadge status={slab.status} />
                      <select
                        value={slab.status}
                        disabled={changingId === slab.id || !canWrite}
                        onChange={(e) => handleStatusChange(slab.id, e.target.value as SlabStatus)}
                        className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary disabled:opacity-50"
                      >
                        {SLAB_STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {statusLabel(s)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
