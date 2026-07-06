"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listBrands, listCollections, listMaterials } from "@/lib/api/catalog";
import { MATERIAL_STATUSES, type Brand, type Collection, type Material, type MaterialStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EntityStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { SortableHeader } from "@/components/ui/sortable-header";
import { ApiRequestError } from "@/lib/api-client";
import { useEntityStatusLabel } from "@/lib/i18n/hooks";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";

export default function MaterialsListPage() {
  const t = useTranslations("catalog");
  const tCommon = useTranslations("common");
  const statusLabel = useEntityStatusLabel();
  const router = useRouter();

  const [materials, setMaterials] = useState<Material[] | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [brandFilter, setBrandFilter] = useState("");
  const [collectionFilter, setCollectionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<MaterialStatus | "">("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("name");
  const [cursor, setCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);

  useEffect(() => {
    listBrands().then((res) => setBrands(res.items)).catch(() => {});
  }, []);

  useEffect(() => {
    listCollections({ brandId: brandFilter || undefined }).then((res) => setCollections(res.items)).catch(() => {});
  }, [brandFilter]);

  const reload = useCallback(
    (append = false) => {
      listMaterials({
        brandId: brandFilter || undefined,
        collectionId: collectionFilter || undefined,
        status: statusFilter || undefined,
        search,
        sort,
        cursor: append ? cursor || undefined : undefined,
      })
        .then((res) => {
          setMaterials((prev) => (append && prev ? [...prev, ...res.items] : res.items));
          setNextCursor(res.next_cursor);
        })
        .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [brandFilter, collectionFilter, statusFilter, search, sort, t]
  );

  useEffect(() => {
    setMaterials(null);
    setCursor(null);
    reload(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandFilter, collectionFilter, statusFilter, search, sort]);

  useListShortcuts({ searchInputRef, onCreate: () => router.push("/catalog/materials/new") });

  function brandName(id: string) {
    return brands.find((b) => b.id === id)?.name ?? tCommon("dash");
  }

  function handleLoadMore() {
    if (!nextCursor) return;
    setCursor(nextCursor);
    reload(true);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("materialsTitle")}</h1>
          <p className="text-sm text-text-secondary">{t("materialsSubtitle")}</p>
        </div>
        <Link href="/catalog/materials/new">
          <Button>{t("createMaterial")}</Button>
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          ref={searchInputRef}
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={t("searchMaterialsPlaceholder")}
          className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        />

        <div className="flex items-center gap-2">
          <label htmlFor="material-brand-filter" className="text-sm text-text-secondary">
            {t("filterByBrand")}
          </label>
          <select
            id="material-brand-filter"
            value={brandFilter}
            onChange={(e) => {
              setBrandFilter(e.target.value);
              setCollectionFilter("");
            }}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{t("allBrands")}</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="material-collection-filter" className="text-sm text-text-secondary">
            {t("filterByCollection")}
          </label>
          <select
            id="material-collection-filter"
            value={collectionFilter}
            onChange={(e) => setCollectionFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{t("allCollections")}</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="material-status-filter" className="text-sm text-text-secondary">
            {t("filterByStatus")}
          </label>
          <select
            id="material-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as MaterialStatus | "")}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{t("allStatuses")}</option>
            {MATERIAL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {materials === null && !error && <TableSkeleton rows={5} columns={5} />}

      {materials && materials.length === 0 && (
        <EmptyState
          title={t("noMaterialsYet")}
          description={t("noMaterialsDesc")}
          action={
            <Link href="/catalog/materials/new">
              <Button>{t("createMaterial")}</Button>
            </Link>
          }
        />
      )}

      {materials && materials.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-border bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
                <tr>
                  <SortableHeader field="name" label={t("tableName")} sort={sort} onSortChange={setSort} />
                  <th className="px-4 py-2 font-medium">{t("tableBrand")}</th>
                  <SortableHeader field="material_type" label={t("tableMaterialType")} sort={sort} onSortChange={setSort} />
                  <th className="px-4 py-2 font-medium">{t("tableColor")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableFinish")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((material) => (
                  <tr
                    key={material.id}
                    onClick={() => router.push(`/catalog/materials/${material.id}`)}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                  >
                    <td className="px-4 py-2">
                      <Link
                        href={`/catalog/materials/${material.id}`}
                        className="font-medium text-primary hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {material.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{brandName(material.brand_id)}</td>
                    <td className="px-4 py-2 text-text-secondary">{material.material_type ?? tCommon("dash")}</td>
                    <td className="px-4 py-2 text-text-secondary">{material.color ?? tCommon("dash")}</td>
                    <td className="px-4 py-2 text-text-secondary">{material.finish ?? tCommon("dash")}</td>
                    <td className="px-4 py-2">
                      <EntityStatusBadge status={material.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={handleLoadMore}>
                {t("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
