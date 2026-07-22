"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { listMaterials, listWarehouses, searchOffcuts } from "@/lib/api/catalog";
import type { Material, Slab, Warehouse } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, CardHeader } from "@/components/ui/card";
import { SlabStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SelectField, TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { useDebouncedValue } from "@/lib/use-debounced-value";

function PlaceholderImage() {
  return (
    <div className="flex h-24 w-full items-center justify-center rounded-md border border-dashed border-border bg-bg text-text-secondary">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <path d="M21 15l-5-5L5 21" />
      </svg>
    </div>
  );
}

export default function OffcutLibraryPage() {
  const t = useTranslations("cutOptimization");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");

  const [materials, setMaterials] = useState<Material[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [offcuts, setOffcuts] = useState<Slab[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [materialId, setMaterialId] = useState("");
  const [thicknessMm, setThicknessMm] = useState("");
  const [finish, setFinish] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [minLengthMm, setMinLengthMm] = useState("");
  const [minWidthMm, setMinWidthMm] = useState("");
  const [minAreaM2, setMinAreaM2] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput, 250);

  useEffect(() => {
    listMaterials({ limit: 100 }).then((r) => setMaterials(r.items)).catch(() => {});
    listWarehouses().then((r) => setWarehouses(r.items)).catch(() => {});
  }, []);

  const load = useCallback(() => {
    searchOffcuts({
      materialId: materialId || undefined,
      thicknessMm: thicknessMm || undefined,
      finish: finish || undefined,
      warehouseId: warehouseId || undefined,
      minLengthMm: minLengthMm || undefined,
      minWidthMm: minWidthMm || undefined,
      minAreaM2: minAreaM2 || undefined,
      search: search || undefined,
    })
      .then((r) => setOffcuts(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [materialId, thicknessMm, finish, warehouseId, minLengthMm, minWidthMm, minAreaM2, search, t]);

  useEffect(() => {
    setOffcuts(null);
    load();
  }, [load]);

  const materialName = (id: string) => materials.find((m) => m.id === id)?.name ?? id;
  const warehouseName = (id: string) => warehouses.find((w) => w.id === id)?.name ?? id;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("inventory"), href: "/catalog/materials" }, { label: t("offcutLibrary") }]} />

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("offcutLibrary")}</h1>
        <p className="text-sm text-text-secondary">{t("offcutLibraryDesc")}</p>
      </div>

      <Card>
        <CardHeader title={tCommon("filters")} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          <SelectField label={t("material")} value={materialId} onChange={(e) => setMaterialId(e.target.value)}>
            <option value="">{tCommon("allMaterials")}</option>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </SelectField>
          <SelectField label={tNav("warehouses")} value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
            <option value="">{tCommon("allWarehouses")}</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </SelectField>
          <TextField label={t("thickness")} value={thicknessMm} onChange={(e) => setThicknessMm(e.target.value)} placeholder="20" />
          <TextField label={t("finish")} value={finish} onChange={(e) => setFinish(e.target.value)} placeholder="Polished" />
          <TextField label={t("minLength")} value={minLengthMm} onChange={(e) => setMinLengthMm(e.target.value)} placeholder="mm" />
          <TextField label={t("minWidth")} value={minWidthMm} onChange={(e) => setMinWidthMm(e.target.value)} placeholder="mm" />
          <TextField label={t("minArea")} value={minAreaM2} onChange={(e) => setMinAreaM2(e.target.value)} placeholder="m²" />
          <TextField label={tCommon("search")} value={searchInput} onChange={(e) => setSearchInput(e.target.value)} />
        </div>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {offcuts === null && !error && <TableSkeleton rows={6} columns={3} />}

      {offcuts && offcuts.length === 0 && (
        <EmptyState title={t("noOffcutsFound")} description={t("noOffcutsDesc")} />
      )}

      {offcuts && offcuts.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {offcuts.map((offcut) => (
            <Card key={offcut.id}>
              <PlaceholderImage />
              <div className="mt-3 flex items-center justify-between">
                <p className="font-mono text-sm font-medium text-text-primary">{offcut.slab_number}</p>
                <SlabStatusBadge status={offcut.status} />
              </div>
              <p className="mt-1 text-xs text-text-secondary">{materialName(offcut.material_id)}</p>
              <p className="text-xs text-text-secondary">{warehouseName(offcut.warehouse_id)}</p>
              <p className="mt-2 text-sm text-text-primary">
                {offcut.length_mm ?? "—"}×{offcut.width_mm ?? "—"}mm
              </p>
              <p className="text-xs text-text-secondary">
                {t("availableArea")}: {offcut.area_m2 ?? "—"} m²
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
