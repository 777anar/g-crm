"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listOrders } from "@/lib/api/orders";
import type { Order, OrderStatus } from "@/lib/types";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { useDebouncedValue } from "@/lib/use-debounced-value";

const STATUS_COLORS: Record<string, string> = {
  waiting: "bg-gray-100 text-gray-700",
  measuring: "bg-yellow-100 text-yellow-700",
  approved_for_production: "bg-blue-100 text-blue-700",
  in_production: "bg-indigo-100 text-indigo-700",
  ready: "bg-purple-100 text-purple-700",
  delivered: "bg-teal-100 text-teal-700",
  installed: "bg-green-100 text-green-700",
  completed: "bg-green-200 text-green-800",
  cancelled: "bg-red-100 text-red-700",
};

export default function OrdersPage() {
  const t = useTranslations("orders");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [orders, setOrders] = useState<Order[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const search = useDebouncedValue(searchInput, 250);

  const load = useCallback(() => {
    listOrders({ status: statusFilter || undefined, search: search || undefined })
      .then((r) => setOrders(r.items))
      .catch((err) =>
        setError(err instanceof ApiRequestError ? err.message : t("loadFailed"))
      );
  }, [statusFilter, search, t]);

  useEffect(() => {
    setOrders(null);
    load();
  }, [load]);

  const ORDER_STATUS_LIST = [
    "waiting", "measuring", "approved_for_production", "in_production",
    "ready", "delivered", "installed", "completed", "cancelled",
  ] as const;

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("title")}</h1>
          <p className="page-subtitle">{t("subtitle")}</p>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <input
          className="input flex-1"
          placeholder={tCommon("search")}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <select
          className="input w-56"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">{tCommon("allStatuses") ?? "All statuses"}</option>
          {ORDER_STATUS_LIST.map((s) => (
            <option key={s} value={s}>{t(s as any)}</option>
          ))}
        </select>
      </div>

      {error && <div className="error-message">{error}</div>}

      {orders === null ? (
        <TableSkeleton />
      ) : orders.length === 0 ? (
        <EmptyState title={t("noOrdersYet")} description={t("noOrdersDesc")} />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("tableOrder")}</th>
                <th>{t("tableStatus")}</th>
                <th>{t("tableProject")}</th>
                <th>{t("tableTotal")}</th>
                <th>{t("scheduledProduction")}</th>
                <th>{t("tableCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr
                  key={o.id}
                  className="clickable-row"
                  onClick={() => router.push(`/orders/${o.id}`)}
                >
                  <td className="font-medium font-mono">{o.order_number}</td>
                  <td>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[o.status] ?? ""}`}
                    >
                      {t(o.status as any)}
                    </span>
                  </td>
                  <td>{o.project_id}</td>
                  <td>
                    {o.currency} {parseFloat(o.total_final).toFixed(2)}
                  </td>
                  <td>
                    {o.scheduled_production_date
                      ? new Date(o.scheduled_production_date).toLocaleDateString()
                      : tCommon("dash")}
                  </td>
                  <td>{new Date(o.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
