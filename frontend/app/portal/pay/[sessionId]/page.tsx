"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { getPortalPaymentSession, simulatePortalPaymentSession } from "@/lib/api/portal";
import type { PortalPaymentSession } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { TableSkeleton } from "@/components/ui/skeleton";

/** Only ever reached when the "mock" gateway is active (its checkout_url is
 * this relative path) -- a real gateway redirects the browser straight to
 * its own hosted checkout page instead. Lets the whole payment flow be
 * demoed end-to-end without real Stripe credentials, mirroring the AI
 * module's mock-provider-by-default philosophy. */
export default function PortalPaySimulatorPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const t = useTranslations("portal");
  const [session, setSession] = useState<PortalPaymentSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPortalPaymentSession(sessionId)
      .then(setSession)
      .finally(() => setLoading(false));
  }, [sessionId]);

  async function handleOutcome(outcome: "completed" | "failed") {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await simulatePortalPaymentSession(sessionId, outcome);
      const query = updated.status === "completed" ? "success" : "cancelled";
      router.push(`/portal/invoices/${updated.invoice_id}?payment=${query}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("paymentFailed"));
      setSubmitting(false);
    }
  }

  if (loading || !session) return <TableSkeleton rows={3} columns={2} />;

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader title={t("mockCheckoutTitle")} subtitle={t("mockCheckoutSubtitle")} />
        <p className="mb-4 text-2xl font-semibold text-text-primary">
          {session.currency} {parseFloat(session.amount).toFixed(2)}
        </p>
        {error && <p className="mb-3 text-sm text-danger">{error}</p>}
        {session.status === "pending" ? (
          <div className="flex flex-col gap-2">
            <Button onClick={() => handleOutcome("completed")} disabled={submitting}>
              {t("simulateSuccessfulPayment")}
            </Button>
            <Button variant="secondary" onClick={() => handleOutcome("failed")} disabled={submitting}>
              {t("simulateFailedPayment")}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-text-secondary">{t(`paymentSessionStatus_${session.status}`)}</p>
        )}
      </Card>
    </div>
  );
}
