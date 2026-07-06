"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listWorkOrders } from "@/lib/api/production";
import { WORK_ORDER_STATUSES, type WorkOrder } from "@/lib/types";
import { WorkOrderStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export default function ProductionPage() {
  const t = useTranslations("production");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [workOrders, setWorkOrders] = useState<WorkOrder[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const search = useDebouncedValue(searchInput, 250);

  const load = useCallback(() => {
    listWorkOrders({ status: statusFilter || undefined, search: search || undefined })
      .then((r) => setWorkOrders(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [statusFilter, search, t]);

  useEffect(() => {
    setWorkOrders(null);
    load();
  }, [load]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
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
          {WORK_ORDER_STATUSES.map((s) => (
            <option key={s} value={s}>{t(s as any)}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {workOrders === null && !error && <TableSkeleton rows={5} columns={4} />}

      {workOrders && workOrders.length === 0 && (
        <EmptyState title={t("noWorkOrdersYet")} description={t("noWorkOrdersDesc")} />
      )}

      {workOrders && workOrders.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("tableWorkOrder")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                <th className="px-4 py-2 font-medium">{t("tableOrder")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {workOrders.map((wo) => (
                <tr
                  key={wo.id}
                  onClick={() => router.push(`/production/${wo.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  <td className="px-4 py-2 font-mono font-medium text-text-primary">{wo.work_order_number}</td>
                  <td className="px-4 py-2"><WorkOrderStatusBadge status={wo.status} /></td>
                  <td className="px-4 py-2 text-text-secondary">{wo.order_id}</td>
                  <td className="px-4 py-2 text-text-secondary">{formatDate(wo.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
