"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { getPortalQuote } from "@/lib/api/portal";
import type { PortalQuote } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, CardHeader } from "@/components/ui/card";
import { QuoteStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";

export default function PortalQuoteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("portal");
  const [quote, setQuote] = useState<PortalQuote | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortalQuote(id)
      .then(setQuote)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !quote) return <TableSkeleton rows={5} columns={3} />;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: t("nav.quotes"), href: "/portal/quotes" }, { label: quote.quote_number }]} />

      <div className="flex items-center gap-3">
        <h1 className="font-mono text-xl font-semibold text-text-primary">{quote.quote_number}</h1>
        <QuoteStatusBadge status={quote.status} />
      </div>

      <Card>
        <CardHeader title={t("quoteDetails")} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs text-text-secondary">{t("subtotal")}</p>
            <p className="text-sm text-text-primary">
              {quote.currency} {parseFloat(quote.subtotal_gross).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("discount")}</p>
            <p className="text-sm text-text-primary">
              {quote.currency} {parseFloat(quote.discount_amount).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("vat")}</p>
            <p className="text-sm text-text-primary">
              {quote.currency} {parseFloat(quote.vat_amount).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("total")}</p>
            <p className="text-base font-semibold text-text-primary">
              {quote.currency} {parseFloat(quote.total_final).toFixed(2)}
            </p>
          </div>
          {quote.valid_until && (
            <div>
              <p className="text-xs text-text-secondary">{t("validUntil")}</p>
              <p className="text-sm text-text-primary">{formatDate(quote.valid_until)}</p>
            </div>
          )}
        </div>
        {quote.customer_notes && (
          <div className="mt-3 border-t border-border pt-3">
            <p className="text-xs text-text-secondary">{t("notesForYou")}</p>
            <p className="text-sm text-text-primary">{quote.customer_notes}</p>
          </div>
        )}
      </Card>

      <p className="text-xs text-text-secondary">
        {t("created")}: {formatDate(quote.created_at)}
      </p>
    </div>
  );
}
