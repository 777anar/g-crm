"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { getSupplier, listPurchaseOrders, purchasingExportUrl } from "@/lib/api/purchasing";
import { PURCHASE_ORDER_STATUSES, type PurchaseOrder } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { PurchaseOrderStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PurchasingTabs } from "@/components/purchasing-tabs";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { SortableHeader } from "@/components/ui/sortable-header";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { usePermission } from "@/lib/permissions";

export default function PurchaseOrdersPage() {
  const t = useTranslations("purchasing");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const canWrite = usePermission("purchasing:purchase_orders:write");

  const [orders, setOrders] = useState<PurchaseOrder[] | null>(null);
  const [supplierNames, setSupplierNames] = useState<Record<string, string>>({});
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const search = useDebouncedValue(searchInput, 250);

  const load = useCallback(
    (options: { append?: boolean; cursor?: string } = {}) => {
      listPurchaseOrders({ status: statusFilter || undefined, search: search || undefined, sort, cursor: options.cursor })
        .then((r) => {
          setOrders((prev) => (options.append && prev ? [...prev, ...r.items] : r.items));
          setNextCursor(r.next_cursor);
          const uniqueSupplierIds = Array.from(new Set(r.items.map((o) => o.supplier_id)));
          Promise.all(
            uniqueSupplierIds.map((id) =>
              getSupplier(id)
                .then((s) => [id, s.name] as const)
                .catch(() => null)
            )
          ).then((pairs) => {
            const resolved = pairs.filter((p): p is readonly [string, string] => p !== null);
            setSupplierNames((prev) => (options.append ? { ...prev, ...Object.fromEntries(resolved) } : Object.fromEntries(resolved)));
          });
        })
        .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    },
    [statusFilter, search, sort, t]
  );

  useEffect(() => {
    setOrders(null);
    load();
  }, [load]);

  function handleLoadMore() {
    if (!nextCursor) return;
    load({ append: true, cursor: nextCursor });
  }

  return (
    <div className="flex flex-col gap-4">
      <PurchasingTabs />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("ordersTitle")}</h1>
          <p className="text-sm text-text-secondary">{t("ordersSubtitle")}</p>
        </div>
        {canWrite && (
          <Link href="/purchasing/orders/new">
            <Button>{t("createOrder")}</Button>
          </Link>
        )}
        <a href={purchasingExportUrl("purchase-orders")}><Button variant="secondary">CSV</Button></a>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={tCommon("search")}
          className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        >
          <option value="">{tCommon("allStatuses")}</option>
          {PURCHASE_ORDER_STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(s as Parameters<typeof t>[0])}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {orders === null && !error && <TableSkeleton rows={5} columns={5} />}

      {orders && orders.length === 0 && (
        <EmptyState
          title={t("noOrdersYet")}
          description={t("noOrdersDesc")}
          action={
            canWrite ? (
              <Link href="/purchasing/orders/new">
                <Button>{t("createOrder")}</Button>
              </Link>
            ) : undefined
          }
        />
      )}

      {orders && orders.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <SortableHeader field="po_number" label={t("tablePoNumber")} sort={sort} onSortChange={setSort} />
                  <SortableHeader field="status" label={t("tableStatus")} sort={sort} onSortChange={setSort} />
                  <th className="px-4 py-2 font-medium">{t("tableSupplier")}</th>
                  <SortableHeader field="total_amount" label={t("tableTotal")} sort={sort} onSortChange={setSort} />
                  <SortableHeader field="expected_delivery_date" label={t("tableExpectedDelivery")} sort={sort} onSortChange={setSort} />
                  <SortableHeader field="created_at" label={t("tableCreated")} sort={sort} onSortChange={setSort} />
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => router.push(`/purchasing/orders/${o.id}`)}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                  >
                    <td className="px-4 py-2 font-mono font-medium text-text-primary">{o.po_number}</td>
                    <td className="px-4 py-2">
                      <PurchaseOrderStatusBadge status={o.status} />
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{supplierNames[o.supplier_id] ?? tCommon("loading")}</td>
                    <td className="px-4 py-2 text-text-primary">
                      {o.currency} {parseFloat(o.total_amount).toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">
                      {o.expected_delivery_date ? formatDate(o.expected_delivery_date) : tCommon("dash")}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{formatDate(o.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={handleLoadMore}>
                {tCommon("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
