"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  getInvoice,
  listInvoiceLines,
  listInvoicePayments,
  recordPayment,
  updateInvoice,
  updateInvoiceStatus,
} from "@/lib/api/finance";
import { getOrder } from "@/lib/api/orders";
import { PAYMENT_METHODS, type Invoice, type InvoiceLine, type Payment } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { InvoiceStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate, formatDateTime } from "@/lib/format";

const inputClasses =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary";

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("finance");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const toast = useToast();

  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [orderNumber, setOrderNumber] = useState<string | null>(null);
  const [lines, setLines] = useState<InvoiceLine[] | null>(null);
  const [payments, setPayments] = useState<Payment[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({ due_date: "", notes: "" });
  const [paymentForm, setPaymentForm] = useState({ amount: "", method: "cash", reference_note: "" });
  const [paymentError, setPaymentError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const inv = await getInvoice(id);
    setInvoice(inv);
    setForm({ due_date: inv.due_date ?? "", notes: inv.notes ?? "" });
    getOrder(inv.order_id).then((o) => setOrderNumber(o.order_number)).catch(() => {});
    const [linesRes, paymentsRes] = await Promise.all([listInvoiceLines(id), listInvoicePayments(id)]);
    setLines(linesRes.items);
    setPayments(paymentsRes.items);
    setLoading(false);
  }, [id]);

  useEffect(() => { reload(); }, [reload]);

  async function handleSend() {
    setBusy(true);
    try {
      await updateInvoiceStatus(id, "sent");
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleMarkOverdue() {
    setBusy(true);
    try {
      await updateInvoiceStatus(id, "overdue");
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    setBusy(true);
    try {
      await updateInvoiceStatus(id, "cancelled", cancelReason || undefined);
      setCancelMode(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveDetails() {
    try {
      await updateInvoice(id, { due_date: form.due_date || null, notes: form.notes || null });
      setEditMode(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  async function handleRecordPayment() {
    setPaymentError(null);
    setBusy(true);
    try {
      await recordPayment(id, {
        amount: paymentForm.amount,
        method: paymentForm.method,
        reference_note: paymentForm.reference_note || undefined,
      });
      setPaymentForm({ amount: "", method: "cash", reference_note: "" });
      await reload();
    } catch (err) {
      setPaymentError(err instanceof Error ? err.message : t("paymentFailed"));
    } finally {
      setBusy(false);
    }
  }

  if (loading || !invoice) return <TableSkeleton rows={5} columns={5} />;

  const isTerminal = invoice.status === "paid" || invoice.status === "cancelled";
  const canRecordPayment = invoice.status === "sent" || invoice.status === "partially_paid" || invoice.status === "overdue";

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        className="print-hidden"
        items={[{ label: tNav("invoices"), href: "/finance/invoices" }, { label: invoice.invoice_number }]}
      />

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-text-primary">{invoice.invoice_number}</h1>
            <InvoiceStatusBadge status={invoice.status} />
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            {t("forOrder")}: <Link href={`/orders/${invoice.order_id}`} className="text-primary hover:underline">{orderNumber ?? tCommon("loading")}</Link>
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => window.print()}>{t("printInvoice")}</Button>
          {!isTerminal && (
            <>
              {invoice.status === "draft" && (
                <Button onClick={handleSend} disabled={busy}>{busy ? t("saving") : t("sendInvoice")}</Button>
              )}
              {invoice.status === "sent" && (
                <Button variant="secondary" onClick={handleMarkOverdue} disabled={busy}>{t("markOverdue")}</Button>
              )}
              {!cancelMode && (
                <Button variant="destructive" onClick={() => setCancelMode(true)}>{t("cancelInvoice")}</Button>
              )}
            </>
          )}
        </div>
      </div>

      {cancelMode && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="mb-2 text-sm font-medium text-danger">{t("cancelReason")}</p>
          <textarea
            className={`${inputClasses} mb-2 w-full`}
            rows={2}
            aria-label={t("cancelReason")}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <div className="flex gap-2">
            <Button onClick={handleCancel} disabled={busy}>{t("cancelInvoice")}</Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      <Card className="flex flex-wrap gap-6 text-sm">
        <div><span className="text-text-secondary">{t("subtotal")}:</span> <strong className="text-text-primary">{invoice.currency} {parseFloat(invoice.subtotal_amount).toFixed(2)}</strong></div>
        <div><span className="text-text-secondary">{t("amountPaid")}:</span> <strong className="text-success">{invoice.currency} {parseFloat(invoice.amount_paid).toFixed(2)}</strong></div>
        <div><span className="text-text-secondary">{t("balanceDue")}:</span> <strong className="text-warning">{invoice.currency} {parseFloat(invoice.balance_due).toFixed(2)}</strong></div>
        <div className="ml-auto text-base"><span className="text-text-secondary">{t("totalAmount")}:</span> <strong className="text-lg text-primary">{invoice.currency} {parseFloat(invoice.total_amount).toFixed(2)}</strong></div>
      </Card>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text-primary">{t("details")}</h2>
          {!isTerminal && (
            <button
              className="text-xs text-primary hover:underline"
              onClick={() => (editMode ? handleSaveDetails() : setEditMode(true))}
            >
              {editMode ? tCommon("save") : tCommon("edit")}
            </button>
          )}
        </div>
        {editMode ? (
          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <div>
              <label className="text-xs text-text-secondary">{t("dueDate")}</label>
              <input
                type="date"
                className={`${inputClasses} mt-0.5 w-full`}
                value={form.due_date}
                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-text-secondary">{t("notes")}</label>
              <input
                className={`${inputClasses} mt-0.5 w-full`}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
          </div>
        ) : (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-xs text-text-secondary">{t("issueDate")}</dt>
              <dd className="text-text-primary">{formatDate(invoice.issue_date)}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">{t("dueDate")}</dt>
              <dd className="text-text-primary">{invoice.due_date ? formatDate(invoice.due_date) : tCommon("dash")}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">{t("notes")}</dt>
              <dd className="text-text-primary">{invoice.notes ?? tCommon("dash")}</dd>
            </div>
          </dl>
        )}
      </Card>

      <Card className="p-0 overflow-hidden">
        <div className="flex items-center justify-between bg-primary px-4 py-3 text-white">
          <h2 className="font-semibold">{t("lineItems")}</h2>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-text-secondary">
            <tr>
              <th className="px-4 py-2 font-medium">{t("description")}</th>
              <th className="px-4 py-2 font-medium">{t("amount")}</th>
            </tr>
          </thead>
          <tbody>
            {lines?.map((line) => (
              <tr key={line.id} className="border-t border-border">
                <td className="px-4 py-2">{line.description}</td>
                <td className="px-4 py-2 font-medium text-text-primary">
                  {invoice.currency} {parseFloat(line.amount).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-text-primary">{t("payments")}</h2>

        {payments && payments.length > 0 ? (
          <div className="overflow-x-auto">
          <table className="mb-4 w-full text-left text-sm">
            <thead className="text-text-secondary">
              <tr>
                <th className="px-2 py-1 font-medium">{t("paidAt")}</th>
                <th className="px-2 py-1 font-medium">{t("paymentMethod")}</th>
                <th className="px-2 py-1 font-medium">{t("amount")}</th>
                <th className="px-2 py-1 font-medium">{t("referenceNote")}</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id} className="border-t border-border">
                  <td className="px-2 py-1 text-text-secondary">{formatDateTime(p.paid_at)}</td>
                  <td className="px-2 py-1">{t(`paymentMethod_${p.method}` as any)}</td>
                  <td className="px-2 py-1 font-medium text-text-primary">
                    {invoice.currency} {parseFloat(p.amount).toFixed(2)}
                  </td>
                  <td className="px-2 py-1 text-text-secondary">{p.reference_note ?? tCommon("dash")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : (
          <p className="mb-4 text-sm text-text-secondary">{t("noPaymentsYet")}</p>
        )}

        {canRecordPayment && (
          <div className="print-hidden flex flex-wrap items-end gap-2 border-t border-border pt-3">
            <div>
              <label className="text-xs text-text-secondary">{t("amount")}</label>
              <input
                className={`${inputClasses} mt-0.5 block w-32`}
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="text-xs text-text-secondary">{t("paymentMethod")}</label>
              <select
                className={`${inputClasses} mt-0.5 block`}
                value={paymentForm.method}
                onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })}
              >
                {PAYMENT_METHODS.map((m) => (
                  <option key={m} value={m}>{t(`paymentMethod_${m}` as any)}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs text-text-secondary">{t("referenceNote")}</label>
              <input
                className={`${inputClasses} mt-0.5 block w-full`}
                value={paymentForm.reference_note}
                onChange={(e) => setPaymentForm({ ...paymentForm, reference_note: e.target.value })}
              />
            </div>
            <Button onClick={handleRecordPayment} disabled={busy || !paymentForm.amount}>
              {busy ? t("saving") : t("recordPayment")}
            </Button>
          </div>
        )}
        {paymentError && <p className="mt-2 text-sm text-danger">{paymentError}</p>}
      </Card>
    </div>
  );
}
