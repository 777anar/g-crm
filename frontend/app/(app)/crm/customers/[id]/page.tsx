"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { addCustomerNote, archiveCustomer, getCustomerProfile, uploadCustomerAttachment } from "@/lib/api/crm";
import type { CustomerProfile } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge, CustomerArchivedBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TextAreaField } from "@/components/ui/field";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString();
}

export default function CustomerProfilePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const customerId = params.id;

  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [noteBody, setNoteBody] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function reload() {
    try {
      const data = await getCustomerProfile(customerId);
      setProfile(data);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to load customer profile.");
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteBody.trim()) return;
    setSavingNote(true);
    try {
      await addCustomerNote(customerId, noteBody);
      setNoteBody("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to add note.");
    } finally {
      setSavingNote(false);
    }
  }

  async function handleArchive() {
    if (!confirm("Archive this customer? They will be hidden from the default customer list.")) return;
    setArchiving(true);
    try {
      await archiveCustomer(customerId);
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to archive customer.");
    } finally {
      setArchiving(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadCustomerAttachment(customerId, file);
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to upload attachment.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  if (error && !profile) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (!profile) {
    return <p className="text-text-secondary">Loading customer profile...</p>;
  }

  const { customer, contacts, attachments, timeline, projects, quotes, orders, payments } = profile;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-text-primary">{customer.name}</h1>
          <CustomerArchivedBadge archived={customer.deleted_at !== null} />
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => router.push("/crm/customers")}>
            Back to list
          </Button>
          {customer.deleted_at === null && (
            <Button variant="destructive" onClick={handleArchive} disabled={archiving}>
              {archiving ? "Archiving..." : "Archive Customer"}
            </Button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-1">
          <Card>
            <CardHeader title="Contact Information" />
            {contacts.length === 0 ? (
              <p className="text-sm text-text-secondary">No contacts on file.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {contacts.map((contact) => (
                  <li key={contact.id} className="text-sm">
                    <p className="font-medium text-text-primary">{contact.full_name}</p>
                    {contact.email && <p className="text-text-secondary">{contact.email}</p>}
                    {contact.phone && <p className="text-text-secondary">{contact.phone}</p>}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title="Company" />
            <dl className="flex flex-col gap-2 text-sm">
              <div>
                <dt className="text-text-secondary">Type</dt>
                <dd className="capitalize text-text-primary">{customer.type}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">Assigned Manager</dt>
                <dd className="text-text-primary">{customer.assigned_manager_id ?? "Unassigned"}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">Lead Source</dt>
                <dd className="text-text-primary">
                  {customer.lead_source ? <Badge tone="info">{customer.lead_source}</Badge> : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">Advertising Campaign</dt>
                <dd className="text-text-primary">{customer.advertising_campaign ?? "—"}</dd>
              </div>
            </dl>
          </Card>

          <Card>
            <CardHeader title="Attachments" />
            <label className="mb-3 block w-fit cursor-pointer rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-bg">
              {uploading ? "Uploading..." : "Upload Attachment"}
              <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
            </label>
            {attachments.length === 0 ? (
              <p className="text-sm text-text-secondary">No attachments yet.</p>
            ) : (
              <ul className="flex flex-col gap-1 text-sm">
                {attachments.map((a) => (
                  <li key={a.id} className="flex items-center justify-between text-text-primary">
                    <span className="truncate">{a.storage_path.split("/").pop()}</span>
                    <span className="text-xs text-text-secondary">{a.mime_type}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <CardHeader title="Projects" />
            {projects.length === 0 ? (
              <EmptyState
                title="No projects yet"
                description="Projects will appear here once the Production module is installed."
              />
            ) : null}
          </Card>
          <Card>
            <CardHeader title="Quotes" />
            {quotes.length === 0 ? (
              <EmptyState title="No quotes yet" description="Quotes will appear here once the Sales module is installed." />
            ) : null}
          </Card>
          <Card>
            <CardHeader title="Orders" />
            {orders.length === 0 ? (
              <EmptyState title="No orders yet" description="Orders will appear here once the Sales module is installed." />
            ) : null}
          </Card>
          <Card>
            <CardHeader title="Payments" />
            {payments.length === 0 ? (
              <EmptyState
                title="No payments yet"
                description="Payments will appear here once the Finance module is installed."
              />
            ) : null}
          </Card>

          <Card>
            <CardHeader title="Customer Notes" />
            <form className="mb-4 flex flex-col gap-2" onSubmit={handleAddNote}>
              <TextAreaField
                label="Add a note"
                value={noteBody}
                onChange={(e) => setNoteBody(e.target.value)}
                placeholder="Write a note about this customer..."
              />
              <div className="flex justify-end">
                <Button type="submit" disabled={savingNote || !noteBody.trim()}>
                  {savingNote ? "Saving..." : "Add Note"}
                </Button>
              </div>
            </form>
          </Card>

          <Card>
            <CardHeader title="Activity Timeline" />
            {timeline.length === 0 ? (
              <EmptyState title="No activity yet" />
            ) : (
              <ul className="flex flex-col gap-3">
                {timeline.map((entry) => (
                  <li key={entry.id} className="border-l-2 border-border pl-3">
                    <div className="flex items-center gap-2">
                      <Badge tone={entry.type === "system" ? "neutral" : "info"}>{entry.type}</Badge>
                      <span className="text-xs text-text-secondary">{formatDate(entry.created_at)}</span>
                    </div>
                    <p className="mt-1 text-sm text-text-primary">{entry.body}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
