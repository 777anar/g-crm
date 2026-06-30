"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { listCustomers } from "@/lib/api/crm";
import type { Customer } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { CustomerArchivedBadge, LeadChannelBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { useCustomerTypeLabel } from "@/lib/i18n/hooks";

export default function CustomersListPage() {
  const t = useTranslations("customers");
  const tCommon = useTranslations("common");
  const customerTypeLabel = useCustomerTypeLabel();
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCustomers(null);
    listCustomers({ includeArchived })
      .then((res) => setCustomers(res.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [includeArchived, t]);

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

      <label className="flex w-fit items-center gap-2 text-sm text-text-secondary">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => setIncludeArchived(e.target.checked)}
        />
        {t("showArchived")}
      </label>

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
                <th className="px-4 py-2 font-medium">{t("tableName")}</th>
                <th className="px-4 py-2 font-medium">{t("tableType")}</th>
                <th className="px-4 py-2 font-medium">{t("tableLeadSource")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCampaign")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr key={customer.id} className="border-b border-border last:border-0 hover:bg-bg">
                  <td className="px-4 py-2">
                    <Link href={`/crm/customers/${customer.id}`} className="font-medium text-primary hover:underline">
                      {customer.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2">{customerTypeLabel(customer.type)}</td>
                  <td className="px-4 py-2">
                    {customer.lead_source ? <LeadChannelBadge channel={customer.lead_source} /> : tCommon("dash")}
                  </td>
                  <td className="px-4 py-2 text-text-secondary">
                    {customer.advertising_campaign ?? tCommon("dash")}
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
