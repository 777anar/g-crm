"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listCustomers } from "@/lib/api/crm";
import type { Customer } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge, CustomerArchivedBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";

export default function CustomersListPage() {
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCustomers(null);
    listCustomers({ includeArchived })
      .then((res) => setCustomers(res.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : "Failed to load customers."));
  }, [includeArchived]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Customers</h1>
          <p className="text-sm text-text-secondary">Manage customer profiles, contacts, and activity.</p>
        </div>
        <Link href="/crm/customers/new">
          <Button>Create Customer</Button>
        </Link>
      </div>

      <label className="flex w-fit items-center gap-2 text-sm text-text-secondary">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => setIncludeArchived(e.target.checked)}
        />
        Show archived
      </label>

      {error && <p className="text-sm text-danger">{error}</p>}

      {customers === null && !error && <TableSkeleton rows={5} columns={5} />}

      {customers && customers.length === 0 && (
        <EmptyState
          title="No customers yet"
          description="Create your first customer to start tracking their profile, notes, and activity."
          action={
            <Link href="/crm/customers/new">
              <Button>Create Customer</Button>
            </Link>
          }
        />
      )}

      {customers && customers.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium">Lead Source</th>
                <th className="px-4 py-2 font-medium">Campaign</th>
                <th className="px-4 py-2 font-medium">Created</th>
                <th className="px-4 py-2 font-medium">Status</th>
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
                  <td className="px-4 py-2 capitalize">{customer.type}</td>
                  <td className="px-4 py-2">
                    {customer.lead_source ? <Badge tone="info">{customer.lead_source}</Badge> : "—"}
                  </td>
                  <td className="px-4 py-2 text-text-secondary">{customer.advertising_campaign ?? "—"}</td>
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
