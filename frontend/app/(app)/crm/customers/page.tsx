"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listCustomers, updateCustomer } from "@/lib/api/crm";
import { CUSTOMER_STATUSES, type Customer, type CustomerStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { CustomerArchivedBadge, LeadChannelBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { SortableHeader } from "@/components/ui/sortable-header";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useCustomerStatusLabel } from "@/lib/i18n/hooks";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";

export default function CustomersListPage() {
  const t = useTranslations("customers");
  const tCommon = useTranslations("common");
  const statusLabel = useCustomerStatusLabel();
  const router = useRouter();

  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [statusFilter, setStatusFilter] = useState<CustomerStatus | "">("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [error, setError] = useState<string | null>(null);
  const [savingStatusId, setSavingStatusId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);

  const reload = useCallback(() => {
    listCustomers({ includeArchived, status: statusFilter || undefined, search, sort })
      .then((res) => setCustomers(res.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [includeArchived, statusFilter, search, sort, t]);

  useEffect(() => {
    setCustomers(null);
    reload();
  }, [reload]);

  useListShortcuts({ searchInputRef, onCreate: () => router.push("/crm/customers/new") });

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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
          <p className="text-sm text-text-secondary">{t("subtitle")}</p>
        </div>
        <Link href="/crm/customers/new">
          <Button>{t("createCustomer")}</Button>
        </Link>
      </div>

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
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 border-b border-border bg-bg text-text-secondary">
              <tr>
                <SortableHeader field="name" label={t("tableName")} sort={sort} onSortChange={setSort} />
                <th className="px-4 py-2 font-medium">{t("tablePhone")}</th>
                <th className="px-4 py-2 font-medium">{t("tableLeadSource")}</th>
                <SortableHeader field="status" label={t("tablePipelineStatus")} sort={sort} onSortChange={setSort} />
                <SortableHeader field="created_at" label={t("tableCreated")} sort={sort} onSortChange={setSort} />
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr
                  key={customer.id}
                  onClick={() => router.push(`/crm/customers/${customer.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  <td className="px-4 py-2">
                    <Link
                      href={`/crm/customers/${customer.id}`}
                      className="font-medium text-primary hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {customer.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-text-secondary">{customer.phone ?? tCommon("dash")}</td>
                  <td className="px-4 py-2">
                    {customer.lead_source ? <LeadChannelBadge channel={customer.lead_source} /> : tCommon("dash")}
                  </td>
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
                  <td className="px-4 py-2 text-text-secondary">{formatDate(customer.created_at)}</td>
                  <td className="px-4 py-2">
                    <CustomerArchivedBadge archived={customer.deleted_at !== null} />
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
