"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listInvoices } from "@/lib/api/finance";
import { INVOICE_STATUSES, type Invoice } from "@/lib/types";
import { InvoiceStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export default function InvoicesPage() {
  const t = useTranslations("finance");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const search = useDebouncedValue(searchInput, 250);

  const load = useCallback(() => {
    listInvoices({ status: statusFilter || undefined, search: search || undefined })
      .then((r) => setInvoices(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [statusFilter, search, t]);

  useEffect(() => {
    setInvoices(null);
    load();
  }, [load]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("invoicesTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("invoicesSubtitle")}</p>
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
          {INVOICE_STATUSES.map((s) => (
            <option key={s} value={s}>{t(s as any)}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {invoices === null && !error && <TableSkeleton rows={5} columns={5} />}

      {invoices && invoices.length === 0 && (
        <EmptyState title={t("noInvoicesYet")} description={t("noInvoicesDesc")} />
      )}

      {invoices && invoices.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("tableInvoice")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                <th className="px-4 py-2 font-medium">{t("tableTotal")}</th>
                <th className="px-4 py-2 font-medium">{t("tableBalanceDue")}</th>
                <th className="px-4 py-2 font-medium">{t("tableIssueDate")}</th>
                <th className="px-4 py-2 font-medium">{t("tableDueDate")}</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((i) => (
                <tr
                  key={i.id}
                  onClick={() => router.push(`/finance/invoices/${i.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  <td className="px-4 py-2 font-mono font-medium text-text-primary">{i.invoice_number}</td>
                  <td className="px-4 py-2"><InvoiceStatusBadge status={i.status} /></td>
                  <td className="px-4 py-2 text-text-primary">{i.currency} {parseFloat(i.total_amount).toFixed(2)}</td>
                  <td className="px-4 py-2 text-text-primary">{i.currency} {parseFloat(i.balance_due).toFixed(2)}</td>
                  <td className="px-4 py-2 text-text-secondary">{formatDate(i.issue_date)}</td>
                  <td className="px-4 py-2 text-text-secondary">
                    {i.due_date ? formatDate(i.due_date) : tCommon("dash")}
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
