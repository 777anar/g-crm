"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { createPriceList, listPriceLists } from "@/lib/api/catalog";
import type { PriceList } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";

export default function PriceListsPage() {
  const t = useTranslations("catalog");
  const tCommon = useTranslations("common");
  const [priceLists, setPriceLists] = useState<PriceList[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("AZN");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(async () => {
    try {
      const res = await listPriceLists();
      setPriceLists(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }, [t]);

  useEffect(() => {
    setPriceLists(null);
    reload();
  }, [reload]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createPriceList({ name, currency });
      setName("");
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
        <h1 className="text-xl font-semibold text-text-primary">{t("priceListsTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("priceListsSubtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("createPriceList")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-3" onSubmit={handleCreate}>
          <TextField label={t("name")} value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          <TextField label={t("currency")} value={currency} onChange={(e) => setCurrency(e.target.value)} maxLength={3} />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !name}>
              {submitting ? t("creating") : t("createPriceList")}
            </Button>
          </div>
        </form>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {priceLists === null && !error && <TableSkeleton rows={4} columns={3} />}

      {priceLists && priceLists.length === 0 && (
        <EmptyState title={t("noPriceListsYet")} description={t("noPriceListsDesc")} />
      )}

      {priceLists && priceLists.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("name")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCurrency")}</th>
                <th className="px-4 py-2 font-medium">{t("tableDefault")}</th>
              </tr>
            </thead>
            <tbody>
              {priceLists.map((priceList) => (
                <tr key={priceList.id} className="border-b border-border last:border-0 hover:bg-bg">
                  <td className="px-4 py-2">
                    <Link
                      href={`/catalog/price-lists/${priceList.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {priceList.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-text-secondary">{priceList.currency}</td>
                  <td className="px-4 py-2">
                    {priceList.is_default ? <Badge tone="success">{tCommon("yes")}</Badge> : tCommon("dash")}
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
