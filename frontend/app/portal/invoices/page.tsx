"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { listPortalInvoices } from "@/lib/api/portal";
import type { PortalInvoice } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { InvoiceStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { formatDate } from "@/lib/format";

export default function PortalInvoicesPage() {
  const t = useTranslations("portal");
  const tCommon = useTranslations("common");
  const [invoices, setInvoices] = useState<PortalInvoice[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const reload = useCallback(async (options: { append?: boolean; cursor?: string } = {}) => {
    const res = await listPortalInvoices({ cursor: options.cursor });
    setInvoices((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
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
        <h1 className="text-xl font-semibold text-text-primary">{t("nav.invoices")}</h1>
      </div>

      {invoices === null && <TableSkeleton rows={4} columns={4} />}
      {invoices && invoices.length === 0 && <EmptyState title={t("noInvoicesYet")} description={t("noInvoicesDesc")} />}

      {invoices && invoices.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("invoiceNumber")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-4 py-2 font-medium">{t("total")}</th>
                  <th className="px-4 py-2 font-medium">{t("balanceDue")}</th>
                  <th className="px-4 py-2 font-medium">{t("dueDate")}</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-mono text-text-primary">
                      <Link href={`/portal/invoices/${invoice.id}`} className="hover:text-primary hover:underline">
                        {invoice.invoice_number}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      <InvoiceStatusBadge status={invoice.status} />
                    </td>
                    <td className="px-4 py-2 text-text-primary">
                      {invoice.currency} {parseFloat(invoice.total_amount).toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-text-primary">
                      {invoice.currency} {parseFloat(invoice.balance_due).toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">
                      {invoice.due_date ? formatDate(invoice.due_date) : tCommon("dash")}
                    </td>
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
