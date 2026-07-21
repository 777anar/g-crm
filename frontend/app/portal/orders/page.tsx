"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { listPortalOrders } from "@/lib/api/portal";
import type { PortalOrder } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { OrderStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { formatDate } from "@/lib/format";

export default function PortalOrdersPage() {
  const t = useTranslations("portal");
  const tCommon = useTranslations("common");
  const [orders, setOrders] = useState<PortalOrder[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const reload = useCallback(async (options: { append?: boolean; cursor?: string } = {}) => {
    const res = await listPortalOrders({ cursor: options.cursor });
    setOrders((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
    setNextCursor(res.next_cursor);
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  function handleLoadMore() {
    if (nextCursor) reload({ append: true, cursor: nextCursor });
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("nav.orders")}</h1>
      </div>

      {orders === null && <TableSkeleton rows={4} columns={4} />}
      {orders && orders.length === 0 && <EmptyState title={t("noOrdersYet")} description={t("noOrdersDesc")} />}

      {orders && orders.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("orderNumber")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-4 py-2 font-medium">{t("total")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-mono text-text-primary">
                      <Link href={`/portal/orders/${order.id}`} className="hover:text-primary hover:underline">
                        {order.order_number}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      <OrderStatusBadge status={order.status} />
                    </td>
                    <td className="px-4 py-2 text-text-primary">
                      {order.currency} {parseFloat(order.total_final).toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{formatDate(order.created_at)}</td>
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
