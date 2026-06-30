"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  addCustomerNote,
  archiveCustomer,
  getCustomerProfile,
  updateCustomer,
  uploadCustomerAttachment,
} from "@/lib/api/crm";
import { CUSTOMER_STATUSES, type CustomerProfile, type CustomerStatus } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge, CustomerArchivedBadge, CustomerStatusBadge, LeadChannelBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TextAreaField } from "@/components/ui/field";
import { Skeleton, TableSkeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";
import { useCustomerStatusLabel } from "@/lib/i18n/hooks";

export default function CustomerProfilePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const customerId = params.id;

  const t = useTranslations("customerProfile");
  const tCommon = useTranslations("common");
  const tActivityType = useTranslations("activityType");
  const statusLabel = useCustomerStatusLabel();

  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [noteBody, setNoteBody] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [customerNotes, setCustomerNotes] = useState("");
  const [savingCustomerNotes, setSavingCustomerNotes] = useState(false);

  async function reload() {
    try {
      const data = await getCustomerProfile(customerId);
      setProfile(data);
      setCustomerNotes(data.customer.notes ?? "");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
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
      setError(err instanceof ApiRequestError ? err.message : t("noteFailed"));
    } finally {
      setSavingNote(false);
    }
  }

  async function handleArchive() {
    if (!confirm(t("archiveConfirm"))) return;
    setArchiving(true);
    try {
      await archiveCustomer(customerId);
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("archiveFailed"));
    } finally {
      setArchiving(false);
    }
  }

  async function handleStatusChange(status: CustomerStatus) {
    setUpdatingStatus(true);
    setError(null);
    try {
      await updateCustomer(customerId, { status });
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function handleSaveCustomerNotes() {
    setSavingCustomerNotes(true);
    setError(null);
    try {
      await updateCustomer(customerId, { notes: customerNotes });
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("noteFailed"));
    } finally {
      setSavingCustomerNotes(false);
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
      setError(err instanceof ApiRequestError ? err.message : t("uploadFailed"));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  if (error && !profile) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (!profile) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-7 w-64" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="flex flex-col gap-4 lg:col-span-1">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
          <div className="lg:col-span-2">
            <TableSkeleton rows={4} columns={3} />
          </div>
        </div>
      </div>
    );
  }

  const { customer, attachments, timeline, projects, quotes, orders, payments } = profile;

  const crossModuleSections = [
    { label: t("projects"), count: projects.length, module: t("viaProduction") },
    { label: t("quotes"), count: quotes.length, module: t("viaSales") },
    { label: t("orders"), count: orders.length, module: t("viaSales") },
    { label: t("payments"), count: payments.length, module: t("viaFinance") },
  ];

  const contactDetails = [
    { label: t("phone"), value: customer.phone },
    { label: t("whatsapp"), value: customer.whatsapp },
    { label: t("instagram"), value: customer.instagram },
    { label: t("facebook"), value: customer.facebook },
    { label: t("email"), value: customer.email },
    { label: t("address"), value: customer.address },
  ];

  return (
    <div className="flex flex-col gap-4">
      <nav className="flex items-center gap-1 text-sm text-text-secondary" aria-label={tCommon("breadcrumb")}>
        <Link href="/crm/customers" className="hover:text-primary hover:underline">
          {t("breadcrumbCustomers")}
        </Link>
        <span>/</span>
        <span className="text-text-primary">{customer.name}</span>
      </nav>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-text-primary">{customer.name}</h1>
          <CustomerArchivedBadge archived={customer.deleted_at !== null} />
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => router.push("/crm/customers")}>
            {t("backToList")}
          </Button>
          {customer.deleted_at === null && (
            <Button variant="destructive" onClick={handleArchive} disabled={archiving}>
              {archiving ? t("archiving") : t("archiveCustomer")}
            </Button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-text-secondary">{t("status")}</span>
          <CustomerStatusBadge status={customer.status} />
          <select
            value={customer.status}
            disabled={updatingStatus}
            onChange={(e) => handleStatusChange(e.target.value as CustomerStatus)}
            className="ml-auto rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary disabled:opacity-50"
          >
            {CUSTOMER_STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-1">
          <Card>
            <CardHeader title={t("contactInformation")} />
            <dl className="flex flex-col gap-2 text-sm">
              {contactDetails.map((detail) => (
                <div key={detail.label}>
                  <dt className="text-text-secondary">{detail.label}</dt>
                  <dd className="text-text-primary">{detail.value || tCommon("dash")}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card>
            <CardHeader title={t("company")} />
            <dl className="flex flex-col gap-2 text-sm">
              <div>
                <dt className="text-text-secondary">{t("companyName")}</dt>
                <dd className="text-text-primary">{customer.company_name ?? tCommon("dash")}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{t("assignedManager")}</dt>
                <dd className="text-text-primary">{customer.assigned_manager_id ?? t("unassigned")}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{t("leadSource")}</dt>
                <dd className="text-text-primary">
                  {customer.lead_source ? <LeadChannelBadge channel={customer.lead_source} /> : tCommon("dash")}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">{t("advertisingCampaign")}</dt>
                <dd className="text-text-primary">{customer.advertising_campaign ?? tCommon("dash")}</dd>
              </div>
            </dl>
          </Card>

          <Card>
            <CardHeader title={t("attachments")} />
            <label className="mb-3 block w-fit cursor-pointer rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-bg">
              {uploading ? t("uploading") : t("uploadAttachment")}
              <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
            </label>
            {attachments.length === 0 ? (
              <p className="text-sm text-text-secondary">{t("noAttachments")}</p>
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
            <CardHeader title={t("crossModuleTitle")} />
            <p className="mb-3 text-xs text-text-secondary">{t("crossModuleHint")}</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {crossModuleSections.map((section) => (
                <div key={section.label} className="rounded-md border border-dashed border-border p-3 text-center">
                  <p className="text-lg font-semibold text-text-secondary">{section.count}</p>
                  <p className="text-xs font-medium text-text-primary">{section.label}</p>
                  <p className="mt-0.5 text-[11px] text-text-secondary">{section.module}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title={t("notes")} />
            <TextAreaField
              label=""
              value={customerNotes}
              onChange={(e) => setCustomerNotes(e.target.value)}
              placeholder={t("addNotePlaceholder")}
            />
            <div className="mt-2 flex justify-end">
              <Button
                onClick={handleSaveCustomerNotes}
                disabled={savingCustomerNotes || customerNotes === (customer.notes ?? "")}
              >
                {savingCustomerNotes ? t("saving") : tCommon("save")}
              </Button>
            </div>
          </Card>

          <Card>
            <CardHeader title={t("customerNotes")} />
            <form className="mb-4 flex flex-col gap-2" onSubmit={handleAddNote}>
              <TextAreaField
                label={t("addNoteLabel")}
                value={noteBody}
                onChange={(e) => setNoteBody(e.target.value)}
                placeholder={t("addNotePlaceholder")}
              />
              <div className="flex justify-end">
                <Button type="submit" disabled={savingNote || !noteBody.trim()}>
                  {savingNote ? t("saving") : t("addNote")}
                </Button>
              </div>
            </form>
          </Card>

          <Card>
            <CardHeader title={t("activityTimeline")} />
            {timeline.length === 0 ? (
              <EmptyState title={t("noActivity")} />
            ) : (
              <ul className="flex flex-col gap-3">
                {timeline.map((entry) => (
                  <li key={entry.id} className="border-l-2 border-border pl-3">
                    <div className="flex items-center gap-2">
                      <Badge tone={entry.type === "system" ? "neutral" : "info"}>{tActivityType(entry.type)}</Badge>
                      <span className="text-xs text-text-secondary">{formatDateTime(entry.created_at)}</span>
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
