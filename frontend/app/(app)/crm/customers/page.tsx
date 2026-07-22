"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { archiveCustomer, exportCustomers, listCustomers, restoreCustomer, updateCustomer } from "@/lib/api/crm";
import { CUSTOMER_STATUSES, type Customer, type CustomerStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { CustomerArchivedBadge, LeadChannelBadge } from "@/components/ui/badge";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { SalesSectionTabs } from "@/components/sales-section-tabs";
import { SortableHeader } from "@/components/ui/sortable-header";
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
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useCustomerStatusLabel } from "@/lib/i18n/hooks";
import { usePermission } from "@/lib/permissions";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";
import { useUrlFilters } from "@/lib/use-url-filters";

const TABLE_ID = "crm-customers";

type CustomersFilters = {
  includeArchived: boolean;
  statusFilter: CustomerStatus | "";
  search: string;
  sort: string;
};

export default function CustomersListPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={5} columns={5} />}>
      <CustomersListPageInner />
    </Suspense>
  );
}

function CustomersListPageInner() {
  const t = useTranslations("customers");
  const tCommon = useTranslations("common");
  const statusLabel = useCustomerStatusLabel();
  const router = useRouter();
  const confirm = useConfirm();
  const toast = useToast();
  const canWrite = usePermission("crm:customers:write");

  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [statusFilter, setStatusFilter] = useState<CustomerStatus | "">("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingStatusId, setSavingStatusId] = useState<string | null>(null);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkStatus, setBulkStatus] = useState<CustomerStatus | "">("");
  const [bulkArchiving, setBulkArchiving] = useState(false);
  const [bulkUpdating, setBulkUpdating] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);

  const columnDefs = [
    { id: "name", label: t("tableName") },
    { id: "phone", label: t("tablePhone") },
    { id: "leadSource", label: t("tableLeadSource") },
    { id: "pipelineStatus", label: t("tablePipelineStatus") },
    { id: "created", label: t("tableCreated") },
    { id: "archived", label: t("tableStatus") },
  ];
  const { isVisible, toggle, reset } = useColumnVisibility(TABLE_ID, columnDefs);
  const { widthOf, startResize } = useResizableColumns(TABLE_ID, {
    name: 200,
    phone: 140,
    leadSource: 140,
    pipelineStatus: 180,
    created: 140,
    archived: 120,
  });
  const savedFilters = useSavedFilters<CustomersFilters>(TABLE_ID);

  useUrlFilters(
    (params) => {
      setIncludeArchived(params.get("archived") === "1");
      setStatusFilter((params.get("status") as CustomerStatus | null) ?? "");
      setSearchInput(params.get("search") ?? "");
      setSort(params.get("sort") ?? "-created_at");
    },
    { archived: includeArchived ? "1" : undefined, status: statusFilter, search, sort: sort === "-created_at" ? undefined : sort }
  );

  const reload = useCallback(
    (options: { append?: boolean; cursor?: string } = {}) => {
      listCustomers({
        includeArchived,
        status: statusFilter || undefined,
        search,
        sort,
        cursor: options.cursor,
      })
        .then((res) => {
          setCustomers((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
          setNextCursor(res.next_cursor);
        })
        .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
    },
    [includeArchived, statusFilter, search, sort, t]
  );

  useEffect(() => {
    setCustomers(null);
    setSelected(new Set());
    reload();
  }, [reload]);

  function handleLoadMore() {
    if (!nextCursor) return;
    reload({ append: true, cursor: nextCursor });
  }

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (!customers) return;
    setSelected((prev) => (prev.size === customers.length ? new Set() : new Set(customers.map((c) => c.id))));
  }

  async function handleBulkArchive() {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    if (!(await confirm(t("confirmBulkArchive", { count: ids.length }), { confirmLabel: t("archiveSelected") }))) return;
    setBulkArchiving(true);
    try {
      const results = await Promise.allSettled(ids.map((id) => archiveCustomer(id)));
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed > 0) {
        toast.error(t("bulkArchivePartialFailure", { succeeded: ids.length - failed, count: ids.length }));
      } else {
        toast.success(t("bulkArchiveSucceeded", { count: ids.length }));
      }
      setSelected(new Set());
      reload();
    } finally {
      setBulkArchiving(false);
    }
  }

  async function handleBulkStatusChange() {
    const ids = Array.from(selected);
    if (ids.length === 0 || !bulkStatus) return;
    setBulkUpdating(true);
    try {
      const results = await Promise.allSettled(ids.map((id) => updateCustomer(id, { status: bulkStatus })));
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed > 0) {
        toast.error(t("bulkStatusPartialFailure", { succeeded: ids.length - failed, count: ids.length }));
      } else {
        toast.success(t("bulkStatusSucceeded", { count: ids.length }));
      }
      setSelected(new Set());
      setBulkStatus("");
      reload();
    } finally {
      setBulkUpdating(false);
    }
  }

  useListShortcuts({ searchInputRef, onCreate: () => router.push("/crm/customers/new") });

  function applyFilters(filters: CustomersFilters) {
    setIncludeArchived(filters.includeArchived);
    setStatusFilter(filters.statusFilter);
    setSearchInput(filters.search);
    setSort(filters.sort);
  }

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      await exportCustomers({ includeArchived, status: statusFilter || undefined, search, sort });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("exportFailed"));
    } finally {
      setExporting(false);
    }
  }

  async function handleQuickStatusChange(customerId: string, status: CustomerStatus) {
    setSavingStatusId(customerId);
    try {
      await updateCustomer(customerId, { status });
      reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    } finally {
      setSavingStatusId(null);
    }
  }

  async function handleQuickRestore(customerId: string) {
    setRestoringId(customerId);
    try {
      await restoreCustomer(customerId);
      toast.success(t("restored"));
      reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("restoreFailed"));
    } finally {
      setRestoringId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <SalesSectionTabs />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
          <p className="text-sm text-text-secondary">{t("subtitle")}</p>
        </div>
        {canWrite && (
          <Link href="/crm/customers/new">
            <Button>{t("createCustomer")}</Button>
          </Link>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={searchInputRef}
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          />

          <label className="flex w-fit items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
            />
            {t("showArchived")}
          </label>

          <div className="flex items-center gap-2">
            <label htmlFor="customer-status-filter" className="text-sm text-text-secondary">
              {t("filterByStatus")}
            </label>
            <select
              id="customer-status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as CustomerStatus | "")}
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            >
              <option value="">{t("allStatuses")}</option>
              {CUSTOMER_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" loading={exporting} onClick={handleExport}>
            {t("exportCsv")}
          </Button>
          <ColumnVisibilityMenu columns={columnDefs} isVisible={isVisible} toggle={toggle} reset={reset} />
        </div>
      </div>

      <SavedFiltersBar
        presets={savedFilters.presets}
        onApply={applyFilters}
        onSave={(name) => savedFilters.save(name, { includeArchived, statusFilter, search: searchInput, sort })}
        onRemove={savedFilters.remove}
      />

      {canWrite && selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-surface px-3 py-2">
          <span className="text-sm font-medium text-text-primary">{t("selectedCount", { count: selected.size })}</span>
          <Button variant="secondary" onClick={() => setSelected(new Set())}>
            {t("clearSelection")}
          </Button>
          <div className="flex items-center gap-2">
            <select
              value={bulkStatus}
              onChange={(e) => setBulkStatus(e.target.value as CustomerStatus | "")}
              className="rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            >
              <option value="">{t("changeStatusTo")}</option>
              {CUSTOMER_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>
            <Button variant="secondary" loading={bulkUpdating} disabled={!bulkStatus} onClick={handleBulkStatusChange}>
              {t("applyStatus")}
            </Button>
          </div>
          <Button variant="destructive" loading={bulkArchiving} onClick={handleBulkArchive}>
            {t("archiveSelected")}
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {customers === null && !error && <TableSkeleton rows={5} columns={5} />}

      {customers && customers.length === 0 && (
        <EmptyState
          title={t("noCustomersYet")}
          description={t("noCustomersDesc")}
          action={
            <Link href="/crm/customers/new">
              <Button>{t("createCustomer")}</Button>
            </Link>
          }
        />
      )}

      {customers && customers.length > 0 && (
        <>
        <div className={tableScrollShellClass}>
          <table className="w-full text-left text-sm">
            <thead className={stickyTheadClass}>
              <tr>
                <th className="w-8 px-4 py-2">
                  {canWrite && (
                    <input
                      type="checkbox"
                      aria-label={t("selectAllCustomers")}
                      checked={selected.size > 0 && selected.size === customers.length}
                      onChange={toggleSelectAll}
                    />
                  )}
                </th>
                {isVisible("name") && (
                  <SortableHeader
                    field="name"
                    label={t("tableName")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("name")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("name")} />}
                  />
                )}
                {isVisible("phone") && (
                  <th className="relative px-4 py-2 font-medium" style={{ width: widthOf("phone") }}>
                    {t("tablePhone")}
                    <ColumnResizeHandle onMouseDown={startResize("phone")} />
                  </th>
                )}
                {isVisible("leadSource") && (
                  <th className="relative px-4 py-2 font-medium" style={{ width: widthOf("leadSource") }}>
                    {t("tableLeadSource")}
                    <ColumnResizeHandle onMouseDown={startResize("leadSource")} />
                  </th>
                )}
                {isVisible("pipelineStatus") && (
                  <SortableHeader
                    field="status"
                    label={t("tablePipelineStatus")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("pipelineStatus")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("pipelineStatus")} />}
                  />
                )}
                {isVisible("created") && (
                  <SortableHeader
                    field="created_at"
                    label={t("tableCreated")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("created")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("created")} />}
                  />
                )}
                {isVisible("archived") && (
                  <th className="px-4 py-2 font-medium" style={{ width: widthOf("archived") }}>
                    {t("tableStatus")}
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr
                  key={customer.id}
                  onClick={() => router.push(`/crm/customers/${customer.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
                    {canWrite && (
                      <input
                        type="checkbox"
                        aria-label={t("selectCustomer", { name: customer.name })}
                        checked={selected.has(customer.id)}
                        onChange={() => toggleSelected(customer.id)}
                      />
                    )}
                  </td>
                  {isVisible("name") && (
                    <td className="px-4 py-2">
                      <Link
                        href={`/crm/customers/${customer.id}`}
                        className="font-medium text-primary hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {customer.name}
                      </Link>
                    </td>
                  )}
                  {isVisible("phone") && (
                    <td className="px-4 py-2 text-text-secondary">{customer.phone ?? tCommon("dash")}</td>
                  )}
                  {isVisible("leadSource") && (
                    <td className="px-4 py-2">
                      {customer.lead_source ? <LeadChannelBadge channel={customer.lead_source} /> : tCommon("dash")}
                    </td>
                  )}
                  {isVisible("pipelineStatus") && (
                    <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
                      <select
                        value={customer.status}
                        disabled={savingStatusId === customer.id}
                        onChange={(e) => handleQuickStatusChange(customer.id, e.target.value as CustomerStatus)}
                        className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary disabled:opacity-50"
                      >
                        {CUSTOMER_STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {statusLabel(s)}
                          </option>
                        ))}
                      </select>
                    </td>
                  )}
                  {isVisible("created") && (
                    <td className="px-4 py-2 text-text-secondary">{formatDate(customer.created_at)}</td>
                  )}
                  {isVisible("archived") && (
                    <td className="px-4 py-2" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-2">
                        <CustomerArchivedBadge archived={customer.deleted_at !== null} />
                        {canWrite && customer.deleted_at !== null && (
                          <button
                            type="button"
                            onClick={() => handleQuickRestore(customer.id)}
                            disabled={restoringId === customer.id}
                            className="text-xs font-medium text-primary hover:underline disabled:opacity-50"
                          >
                            {restoringId === customer.id ? t("restoring") : t("restoreCustomer")}
                          </button>
                        )}
                      </div>
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
