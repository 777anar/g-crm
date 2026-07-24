"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { exportFinanceData, listInvoices, type FinanceExportResource } from "@/lib/api/finance";
import { INVOICE_STATUSES, type Invoice } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { usePermission } from "@/lib/permissions";
import { InvoiceStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import {
  ColumnResizeHandle,
  ColumnVisibilityMenu,
  SavedFiltersBar,
  stickyTheadClass,
  tableScrollShellClass,
  useColumnVisibility,
  useResizableColumns,
  useSavedFilters,
} from "@/components/ui/data-table";
import { SortableHeader } from "@/components/ui/sortable-header";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

const TABLE_ID = "finance-invoices";

type InvoicesFilters = { statusFilter: string; search: string; sort?: string };

export default function InvoicesPage() {
  const t = useTranslations("finance");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<FinanceExportResource | null>(null);
  const search = useDebouncedValue(searchInput, 250);
  const canExport = usePermission("finance:export:read");

  async function handleExport(resource: FinanceExportResource) {
    setExporting(resource);
    try {
      await exportFinanceData(resource);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("exportFailed"));
    } finally {
      setExporting(null);
    }
  }

  const columnDefs = [
    { id: "number", label: t("tableInvoice") },
    { id: "status", label: t("tableStatus") },
    { id: "total", label: t("tableTotal") },
    { id: "balance", label: t("tableBalanceDue") },
    { id: "issueDate", label: t("tableIssueDate") },
    { id: "dueDate", label: t("tableDueDate") },
  ];
  const { isVisible, toggle, reset } = useColumnVisibility(TABLE_ID, columnDefs);
  const { widthOf, startResize } = useResizableColumns(TABLE_ID, {
    number: 160,
    status: 140,
    total: 140,
    balance: 140,
    issueDate: 140,
    dueDate: 140,
  });
  const savedFilters = useSavedFilters<InvoicesFilters>(TABLE_ID);

  const load = useCallback(
    (options: { append?: boolean; cursor?: string } = {}) => {
      listInvoices({
        status: statusFilter || undefined,
        search: search || undefined,
        sort,
        cursor: options.cursor,
      })
        .then((r) => {
          setInvoices((prev) => (options.append && prev ? [...prev, ...r.items] : r.items));
          setNextCursor(r.next_cursor);
        })
        .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    },
    [statusFilter, search, sort, t]
  );

  useEffect(() => {
    setInvoices(null);
    load();
  }, [load]);

  function handleLoadMore() {
    if (!nextCursor) return;
    load({ append: true, cursor: nextCursor });
  }

  function applyFilters(filters: InvoicesFilters) {
    setStatusFilter(filters.statusFilter);
    setSearchInput(filters.search);
    if (filters.sort) setSort(filters.sort);
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("invoicesTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("invoicesSubtitle")}</p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
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
            {INVOICE_STATUSES.map((s) => (
              <option key={s} value={s}>{t(s as Parameters<typeof t>[0])}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          {canExport && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-text-secondary">{t("accountingExport")}:</span>
              {(["invoices", "payments", "expenses", "journal"] as const).map((resource) => (
                <Button
                  key={resource}
                  variant="secondary"
                  onClick={() => handleExport(resource)}
                  disabled={exporting !== null}
                >
                  {exporting === resource ? tCommon("loading") : t(`export_${resource}` as Parameters<typeof t>[0])}
                </Button>
              ))}
            </div>
          )}
          <ColumnVisibilityMenu columns={columnDefs} isVisible={isVisible} toggle={toggle} reset={reset} />
        </div>
      </div>

      <SavedFiltersBar
        presets={savedFilters.presets}
        onApply={applyFilters}
        onSave={(name) => savedFilters.save(name, { statusFilter, search: searchInput, sort })}
        onRemove={savedFilters.remove}
      />

      {error && <p className="text-sm text-danger">{error}</p>}

      {invoices === null && !error && <TableSkeleton rows={5} columns={5} />}

      {invoices && invoices.length === 0 && (
        <EmptyState title={t("noInvoicesYet")} description={t("noInvoicesDesc")} />
      )}

      {invoices && invoices.length > 0 && (
        <>
        <div className={tableScrollShellClass}>
          <table className="w-full text-left text-sm">
            <thead className={stickyTheadClass}>
              <tr>
                {isVisible("number") && (
                  <SortableHeader
                    field="invoice_number"
                    label={t("tableInvoice")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("number")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("number")} />}
                  />
                )}
                {isVisible("status") && (
                  <SortableHeader
                    field="status"
                    label={t("tableStatus")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("status")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("status")} />}
                  />
                )}
                {isVisible("total") && (
                  <SortableHeader
                    field="total_amount"
                    label={t("tableTotal")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("total")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("total")} />}
                  />
                )}
                {isVisible("balance") && (
                  <th className="relative px-4 py-2 font-medium" style={{ width: widthOf("balance") }}>
                    {t("tableBalanceDue")}
                    <ColumnResizeHandle onMouseDown={startResize("balance")} />
                  </th>
                )}
                {isVisible("issueDate") && (
                  <th className="relative px-4 py-2 font-medium" style={{ width: widthOf("issueDate") }}>
                    {t("tableIssueDate")}
                    <ColumnResizeHandle onMouseDown={startResize("issueDate")} />
                  </th>
                )}
                {isVisible("dueDate") && (
                  <SortableHeader
                    field="due_date"
                    label={t("tableDueDate")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("dueDate")}
                  />
                )}
              </tr>
            </thead>
            <tbody>
              {invoices.map((i) => (
                <tr
                  key={i.id}
                  onClick={() => router.push(`/finance/invoices/${i.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  {isVisible("number") && (
                    <td className="px-4 py-2 font-mono font-medium text-text-primary">{i.invoice_number}</td>
                  )}
                  {isVisible("status") && (
                    <td className="px-4 py-2"><InvoiceStatusBadge status={i.status} /></td>
                  )}
                  {isVisible("total") && (
                    <td className="px-4 py-2 text-text-primary">{i.currency} {parseFloat(i.total_amount).toFixed(2)}</td>
                  )}
                  {isVisible("balance") && (
                    <td className="px-4 py-2 text-text-primary">{i.currency} {parseFloat(i.balance_due).toFixed(2)}</td>
                  )}
                  {isVisible("issueDate") && (
                    <td className="px-4 py-2 text-text-secondary">{formatDate(i.issue_date)}</td>
                  )}
                  {isVisible("dueDate") && (
                    <td className="px-4 py-2 text-text-secondary">
                      {i.due_date ? formatDate(i.due_date) : tCommon("dash")}
                    </td>
                  )}
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
