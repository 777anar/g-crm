"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listCustomers, listLeads } from "@/lib/api/crm";
import { me } from "@/lib/api/auth";
import type { Customer, Lead } from "@/lib/types";
import { LEAD_SOURCE_CHANNELS } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { Badge, LeadStatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";

const CHANNEL_LABELS: Record<string, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  messenger: "Messenger",
  whatsapp: "WhatsApp",
  manual: "Manual",
};

export default function DashboardPage() {
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
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Failed to load dashboard data."));
  }, []);

  const loading = customers === null || leads === null;

  const activeCustomers = customers?.filter((c) => c.deleted_at === null) ?? [];
  const archivedCustomers = customers?.filter((c) => c.deleted_at !== null) ?? [];
  const convertedLeads = leads?.filter((l) => l.status === "converted") ?? [];
  const openLeads = leads?.filter((l) => l.status !== "converted" && l.status !== "disqualified") ?? [];

  const leadsByChannel = LEAD_SOURCE_CHANNELS.map((channel) => ({
    channel,
    count: leads?.filter((l) => l.source_channel === channel).length ?? 0,
  }));

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
            {fullName ? `Welcome back, ${fullName.split(" ")[0]}` : "Dashboard"}
          </h1>
          <p className="text-sm text-text-secondary">
            {role ? `Signed in as ${role}` : "Overview of your CRM activity"}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/crm/leads">
            <Button variant="secondary">Capture Lead</Button>
          </Link>
          <Link href="/crm/customers/new">
            <Button>Create Customer</Button>
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
            <StatCard label="Active Customers" value={activeCustomers.length} tone="primary" />
            <StatCard label="Archived Customers" value={archivedCustomers.length} />
            <StatCard label="Open Leads" value={openLeads.length} tone="warning" />
            <StatCard label="Converted Leads" value={convertedLeads.length} tone="success" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title="Recent Customers" action={<Link href="/crm/customers" className="text-sm text-primary hover:underline">View all</Link>} />
              {recentCustomers.length === 0 ? (
                <EmptyState title="No customers yet" description="Create your first customer to see it here." />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {recentCustomers.map((customer) => (
                    <li key={customer.id} className="flex items-center justify-between py-2">
                      <div>
                        <Link href={`/crm/customers/${customer.id}`} className="font-medium text-primary hover:underline">
                          {customer.name}
                        </Link>
                        <p className="text-xs text-text-secondary">Created {formatDate(customer.created_at)}</p>
                      </div>
                      {customer.lead_source && <Badge tone="info">{customer.lead_source}</Badge>}
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title="Leads by Channel" />
              <ul className="flex flex-col gap-3">
                {leadsByChannel.map(({ channel, count }) => {
                  const max = Math.max(...leadsByChannel.map((c) => c.count), 1);
                  const pct = Math.round((count / max) * 100);
                  return (
                    <li key={channel}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="text-text-primary">{CHANNEL_LABELS[channel]}</span>
                        <span className="text-text-secondary">{count}</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-bg">
                        <div className="h-1.5 rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </Card>
          </div>

          <Card>
            <CardHeader title="Recent Leads" action={<Link href="/crm/leads" className="text-sm text-primary hover:underline">View all</Link>} />
            {recentLeads.length === 0 ? (
              <EmptyState title="No leads yet" description="Capture your first lead to see it here." />
            ) : (
              <div className="overflow-hidden rounded-md border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border bg-bg text-text-secondary">
                    <tr>
                      <th className="px-4 py-2 font-medium">Name</th>
                      <th className="px-4 py-2 font-medium">Channel</th>
                      <th className="px-4 py-2 font-medium">Status</th>
                      <th className="px-4 py-2 font-medium">Captured</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentLeads.map((lead) => (
                      <tr key={lead.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-2 font-medium text-text-primary">{lead.full_name}</td>
                        <td className="px-4 py-2">
                          <Badge tone="info">{CHANNEL_LABELS[lead.source_channel]}</Badge>
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
