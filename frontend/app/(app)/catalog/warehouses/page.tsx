"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { createWarehouse, listWarehouses } from "@/lib/api/catalog";
import type { Warehouse } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { EntityStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";

export default function WarehousesPage() {
  const t = useTranslations("catalog");
  const tCommon = useTranslations("common");
  const [warehouses, setWarehouses] = useState<Warehouse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(async () => {
    try {
      const res = await listWarehouses();
      setWarehouses(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }, [t]);

  useEffect(() => {
    setWarehouses(null);
    reload();
  }, [reload]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createWarehouse({ name, address: address || undefined });
      setName("");
      setAddress("");
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
        <h1 className="text-xl font-semibold text-text-primary">{t("warehousesTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("warehousesSubtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("createWarehouse")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
          <TextField label={t("name")} value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          <TextField label={t("address")} value={address} onChange={(e) => setAddress(e.target.value)} />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !name}>
              {submitting ? t("creating") : t("createWarehouse")}
            </Button>
          </div>
        </form>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {warehouses === null && !error && <TableSkeleton rows={4} columns={3} />}

      {warehouses && warehouses.length === 0 && (
        <EmptyState title={t("noWarehousesYet")} description={t("noWarehousesDesc")} />
      )}

      {warehouses && warehouses.length > 0 && (
        <div className={tableScrollShellClass}>
          <table className="w-full text-left text-sm">
            <thead className={stickyTheadClass}>
              <tr>
                <th className="px-4 py-2 font-medium">{t("name")}</th>
                <th className="px-4 py-2 font-medium">{t("tableAddress")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {warehouses.map((warehouse) => (
                <tr key={warehouse.id} className="border-b border-border last:border-0 hover:bg-bg">
                  <td className="px-4 py-2 font-medium text-text-primary">{warehouse.name}</td>
                  <td className="px-4 py-2 text-text-secondary">{warehouse.address ?? tCommon("dash")}</td>
                  <td className="px-4 py-2">
                    <EntityStatusBadge status={warehouse.status} />
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
