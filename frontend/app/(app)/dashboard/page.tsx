"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { listCustomers, listLeads } from "@/lib/api/crm";
import { me } from "@/lib/api/auth";
import { CUSTOMER_STATUSES, type Customer, type Lead } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { Badge, CustomerStatusBadge, LeadStatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import { useCustomerStatusLabel, useLeadChannelLabel } from "@/lib/i18n/hooks";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const channelLabel = useLeadChannelLabel();
  const statusLabel = useCustomerStatusLabel();
  const [fullName, setFullName] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      me(),
      listCustomers({ includeArchived: true, limit: 100 }),
      listLeads({ limit: 100 }),
    ])
      .then(([profile, customerRes, leadRes]) => {
        setFullName(profile.full_name);
        setRole(profile.role);
        setCustomers(customerRes.items);
        setLeads(leadRes.items);
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  const loading = customers === null || leads === null;

  const activeCustomers = customers?.filter((c) => c.deleted_at === null) ?? [];

  const customersByStatus = CUSTOMER_STATUSES.map((status) => ({
    status,
    count: activeCustomers.filter((c) => c.status === status).length,
  }));

  const newInquiries = activeCustomers.filter((c) => c.status === "new_inquiry").length;
  const inProduction = activeCustomers.filter(
    (c) => c.status === "in_production" || c.status === "installation_scheduled"
  ).length;
  const lostCustomers = activeCustomers.filter((c) => c.status === "lost").length;

  const recentCustomers = [...activeCustomers]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  const recentLeads = [...(leads ?? [])]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">
            {fullName ? t("welcomeBack", { name: fullName.split(" ")[0] }) : t("title")}
          </h1>
          <p className="text-sm text-text-secondary">{role ? t("signedInAs", { role }) : t("overview")}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/crm/leads">
            <Button variant="secondary">{t("captureLead")}</Button>
          </Link>
          <Link href="/crm/customers/new">
            <Button>{t("createCustomer")}</Button>
          </Link>
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {loading && !error && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <TableSkeleton rows={5} columns={3} />
        </div>
      )}

      {!loading && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label={t("statActiveCustomers")} value={activeCustomers.length} tone="primary" />
            <StatCard label={statusLabel("new_inquiry")} value={newInquiries} tone="info" />
            <StatCard label={t("statInProduction")} value={inProduction} tone="warning" />
            <StatCard label={statusLabel("lost")} value={lostCustomers} tone="danger" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader
                title={t("recentCustomers")}
                action={
                  <Link href="/crm/customers" className="text-sm text-primary hover:underline">
                    {tCommon("viewAll")}
                  </Link>
                }
              />
              {recentCustomers.length === 0 ? (
                <EmptyState title={t("noCustomersYet")} description={t("noCustomersDesc")} />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {recentCustomers.map((customer) => (
                    <li key={customer.id} className="flex items-center justify-between py-2">
                      <div>
                        <Link href={`/crm/customers/${customer.id}`} className="font-medium text-primary hover:underline">
                          {customer.name}
                        </Link>
                        <p className="text-xs text-text-secondary">
                          {t("createdOn", { date: formatDate(customer.created_at) })}
                        </p>
                      </div>
                      <CustomerStatusBadge status={customer.status} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title={t("customersByStatus")} />
              <ul className="flex flex-col gap-3">
                {customersByStatus
                  .filter(({ count }) => count > 0)
                  .map(({ status, count }) => {
                    const max = Math.max(...customersByStatus.map((c) => c.count), 1);
                    const pct = Math.round((count / max) * 100);
                    return (
                      <li key={status}>
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="text-text-primary">{statusLabel(status)}</span>
                          <span className="text-text-secondary">{count}</span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-bg">
                          <div className="h-1.5 rounded-full bg-primary" style={{ width: `${pct}%` }} />
                        </div>
                      </li>
                    );
                  })}
                {customersByStatus.every(({ count }) => count === 0) && (
                  <p className="text-sm text-text-secondary">{t("noCustomersYet")}</p>
                )}
              </ul>
            </Card>
          </div>

          <Card>
            <CardHeader
              title={t("recentLeads")}
              action={
                <Link href="/crm/leads" className="text-sm text-primary hover:underline">
                  {tCommon("viewAll")}
                </Link>
              }
            />
            {recentLeads.length === 0 ? (
              <EmptyState title={t("noLeadsYet")} description={t("noLeadsDesc")} />
            ) : (
              <div className="overflow-hidden rounded-md border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border bg-bg text-text-secondary">
                    <tr>
                      <th className="px-4 py-2 font-medium">{t("tableName")}</th>
                      <th className="px-4 py-2 font-medium">{t("tableChannel")}</th>
                      <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                      <th className="px-4 py-2 font-medium">{t("tableCaptured")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentLeads.map((lead) => (
                      <tr key={lead.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-2 font-medium text-text-primary">{lead.full_name}</td>
                        <td className="px-4 py-2">
                          <Badge tone="info">{channelLabel(lead.source_channel)}</Badge>
                        </td>
                        <td className="px-4 py-2">
                          <LeadStatusBadge status={lead.status} />
                        </td>
                        <td className="px-4 py-2 text-text-secondary">{formatDate(lead.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
