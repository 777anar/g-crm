"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { createPortalPaymentSession, getPortalInvoice } from "@/lib/api/portal";
import type { PortalInvoice } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { InvoiceStatusBadge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";

const PAYABLE_STATUSES = new Set(["sent", "partially_paid", "overdue"]);

export default function PortalInvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useTranslations("portal");
  const tCommon = useTranslations("common");
  const [invoice, setInvoice] = useState<PortalInvoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const paymentResult = searchParams.get("payment");

  useEffect(() => {
    getPortalInvoice(id)
      .then(setInvoice)
      .finally(() => setLoading(false));
  }, [id]);

  async function handlePayNow() {
    setPaying(true);
    setError(null);
    try {
      const session = await createPortalPaymentSession(id);
      if (session.checkout_url.startsWith("http")) {
        window.location.href = session.checkout_url;
      } else {
        router.push(session.checkout_url);
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("paymentFailed"));
      setPaying(false);
    }
  }

  if (loading || !invoice) return <TableSkeleton rows={5} columns={3} />;

  const balanceDue = parseFloat(invoice.balance_due);
  const canPay = PAYABLE_STATUSES.has(invoice.status) && balanceDue > 0;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: t("nav.invoices"), href: "/portal/invoices" }, { label: invoice.invoice_number }]} />

      <div className="flex items-center gap-3">
        <h1 className="font-mono text-xl font-semibold text-text-primary">{invoice.invoice_number}</h1>
        <InvoiceStatusBadge status={invoice.status} />
      </div>

      {paymentResult === "success" && <p className="text-sm text-success">{t("paymentSuccessNotice")}</p>}
      {paymentResult === "cancelled" && <p className="text-sm text-text-secondary">{t("paymentCancelledNotice")}</p>}
      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label={t("total")} value={`${invoice.currency} ${parseFloat(invoice.total_amount).toFixed(2)}`} />
        <StatCard
          label={t("amountPaid")}
          value={`${invoice.currency} ${parseFloat(invoice.amount_paid).toFixed(2)}`}
          tone="success"
        />
        <StatCard
          label={t("balanceDue")}
          value={`${invoice.currency} ${balanceDue.toFixed(2)}`}
          tone={balanceDue > 0 ? "warning" : "success"}
        />
      </div>

      {canPay && (
        <div className="flex justify-end">
          <Button onClick={handlePayNow} disabled={paying}>
            {paying ? t("startingPayment") : t("payNow")}
          </Button>
        </div>
      )}

      <Card>
        <CardHeader title={t("invoiceDetails")} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs text-text-secondary">{t("issueDate")}</p>
            <p className="text-sm text-text-primary">{formatDate(invoice.issue_date)}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("dueDate")}</p>
            <p className="text-sm text-text-primary">
              {invoice.due_date ? formatDate(invoice.due_date) : tCommon("dash")}
            </p>
          </div>
        </div>
        {invoice.notes && (
          <div className="mt-3 border-t border-border pt-3">
            <p className="text-xs text-text-secondary">{t("notesForYou")}</p>
            <p className="text-sm text-text-primary">{invoice.notes}</p>
          </div>
        )}
      </Card>
    </div>
  );
}
