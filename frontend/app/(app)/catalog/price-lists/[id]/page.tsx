"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { listMaterials, listPriceListEntries, upsertPriceListEntry } from "@/lib/api/catalog";
import type { Material, PriceListEntry } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextField } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";

export default function PriceListDetailPage() {
  const params = useParams<{ id: string }>();
  const priceListId = params.id;
  const t = useTranslations("catalog");
  const tDetail = useTranslations("catalog.materialDetail");
  const tCommon = useTranslations("common");

  const [entries, setEntries] = useState<PriceListEntry[] | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [materialId, setMaterialId] = useState("");
  const [costPrice, setCostPrice] = useState("0");
  const [salePrice, setSalePrice] = useState("0");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(async () => {
    try {
      const res = await listPriceListEntries(priceListId);
      setEntries(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : tDetail("loadFailed"));
    }
  }, [priceListId, tDetail]);

  useEffect(() => {
    setEntries(null);
    reload();
  }, [reload]);

  useEffect(() => {
    listMaterials({ limit: 100 }).then((res) => {
      setMaterials(res.items);
      if (res.items.length > 0) setMaterialId((current) => current || res.items[0].id);
    }).catch(() => {});
  }, []);

  function materialName(id: string) {
    return materials.find((m) => m.id === id)?.name ?? id.slice(0, 8);
  }

  async function handleUpsert(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await upsertPriceListEntry(priceListId, { material_id: materialId, cost_price: costPrice, sale_price: salePrice });
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Link href="/catalog/price-lists" className="text-sm text-primary hover:underline">
        ← {tDetail("back")}
      </Link>

      <Card>
        <CardHeader title={t("priceListsTitle")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-4" onSubmit={handleUpsert}>
          <SelectField label={t("material")} value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </SelectField>
          <TextField label={t("costPrice")} value={costPrice} onChange={(e) => setCostPrice(e.target.value)} />
          <TextField label={t("salePrice")} value={salePrice} onChange={(e) => setSalePrice(e.target.value)} />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !materialId}>
              {submitting ? t("saving") : tCommon("save")}
            </Button>
          </div>
        </form>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {entries === null && !error && <Skeleton className="h-40 w-full" />}

      {entries && entries.length === 0 && <p className="text-sm text-text-secondary">{tDetail("noPrices")}</p>}

      {entries && entries.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("material")}</th>
                <th className="px-4 py-2 font-medium">{t("costPrice")}</th>
                <th className="px-4 py-2 font-medium">{t("salePrice")}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 font-medium text-text-primary">{materialName(entry.material_id)}</td>
                  <td className="px-4 py-2 text-text-secondary">{entry.cost_price}</td>
                  <td className="px-4 py-2 text-text-secondary">{entry.sale_price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
