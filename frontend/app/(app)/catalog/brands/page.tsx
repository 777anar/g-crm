"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { createBrand, listBrands } from "@/lib/api/catalog";
import type { Brand } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { EntityStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";

const CREATE_FORM_NAME_INPUT_ID = "brand-create-name";

export default function BrandsPage() {
  const t = useTranslations("catalog");
  const tCommon = useTranslations("common");
  const [brands, setBrands] = useState<Brand[] | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(async () => {
    try {
      const res = await listBrands({ search });
      setBrands(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }, [search, t]);

  useEffect(() => {
    setBrands(null);
    reload();
  }, [reload]);

  useListShortcuts({
    searchInputRef,
    onCreate: () => document.getElementById(CREATE_FORM_NAME_INPUT_ID)?.focus(),
  });

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createBrand({ name, description: description || undefined });
      setName("");
      setDescription("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("brandsTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("brandsSubtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("createBrand")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
          <TextField
            id={CREATE_FORM_NAME_INPUT_ID}
            label={t("name")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <TextField label={t("description")} value={description} onChange={(e) => setDescription(e.target.value)} />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !name}>
              {submitting ? t("creating") : t("createBrand")}
            </Button>
          </div>
        </form>
      </Card>

      <input
        ref={searchInputRef}
        type="search"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder={t("searchBrandsPlaceholder")}
        className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
      />

      {error && <p className="text-sm text-danger">{error}</p>}

      {brands === null && !error && <TableSkeleton rows={4} columns={3} />}

      {brands && brands.length === 0 && <EmptyState title={t("noBrandsYet")} description={t("noBrandsDesc")} />}

      {brands && brands.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("name")}</th>
                <th className="px-4 py-2 font-medium">{t("description")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {brands.map((brand) => (
                <tr key={brand.id} className="border-b border-border last:border-0 hover:bg-bg">
                  <td className="px-4 py-2 font-medium text-text-primary">{brand.name}</td>
                  <td className="px-4 py-2 text-text-secondary">{brand.description ?? tCommon("dash")}</td>
                  <td className="px-4 py-2">
                    <EntityStatusBadge status={brand.status} />
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
