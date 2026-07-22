"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listWorkOrders } from "@/lib/api/production";
import { getOrder } from "@/lib/api/orders";
import { WORK_ORDER_STATUSES, type WorkOrder } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { WorkOrderPriorityBadge, WorkOrderStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { SortableHeader } from "@/components/ui/sortable-header";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export default function ProductionPage() {
  const t = useTranslations("production");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [workOrders, setWorkOrders] = useState<WorkOrder[] | null>(null);
  const [orderNumbers, setOrderNumbers] = useState<Record<string, string>>({});
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const search = useDebouncedValue(searchInput, 250);

  const load = useCallback(
    (options: { append?: boolean; cursor?: string } = {}) => {
      listWorkOrders({
        status: statusFilter || undefined,
        search: search || undefined,
        sort,
        cursor: options.cursor,
      })
        .then((r) => {
          setWorkOrders((prev) => (options.append && prev ? [...prev, ...r.items] : r.items));
          setNextCursor(r.next_cursor);
          const uniqueOrderIds = Array.from(new Set(r.items.map((wo) => wo.order_id)));
          Promise.all(
            uniqueOrderIds.map((id) =>
              getOrder(id)
                .then((o) => [id, o.order_number] as const)
                .catch(() => null)
            )
          ).then((pairs) => {
            const resolved = pairs.filter((p): p is readonly [string, string] => p !== null);
            setOrderNumbers((prev) => (options.append ? { ...prev, ...Object.fromEntries(resolved) } : Object.fromEntries(resolved)));
          });
        })
        .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    },
    [statusFilter, search, sort, t]
  );

  useEffect(() => {
    setWorkOrders(null);
    load();
  }, [load]);

  function handleLoadMore() {
    if (!nextCursor) return;
    load({ append: true, cursor: nextCursor });
  }

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
            <option key={s} value={s}>{t(s as Parameters<typeof t>[0])}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {workOrders === null && !error && <TableSkeleton rows={5} columns={4} />}

      {workOrders && workOrders.length === 0 && (
        <EmptyState title={t("noWorkOrdersYet")} description={t("noWorkOrdersDesc")} />
      )}

      {workOrders && workOrders.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <SortableHeader field="work_order_number" label={t("tableWorkOrder")} sort={sort} onSortChange={setSort} />
                  <SortableHeader field="status" label={t("tableStatus")} sort={sort} onSortChange={setSort} />
                  <SortableHeader field="priority" label={t("tablePriority")} sort={sort} onSortChange={setSort} />
                  <th className="px-4 py-2 font-medium">{t("tableOrder")}</th>
                  <SortableHeader
                    field="scheduled_completion_date"
                    label={t("tableDueDate")}
                    sort={sort}
                    onSortChange={setSort}
                  />
                  <SortableHeader field="created_at" label={t("tableCreated")} sort={sort} onSortChange={setSort} />
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
                    <td className="px-4 py-2"><WorkOrderPriorityBadge priority={wo.priority} /></td>
                    <td className="px-4 py-2 text-text-secondary">{orderNumbers[wo.order_id] ?? tCommon("loading")}</td>
                    <td className="px-4 py-2 text-text-secondary">
                      {wo.scheduled_completion_date ? formatDate(wo.scheduled_completion_date) : tCommon("dash")}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{formatDate(wo.created_at)}</td>
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
