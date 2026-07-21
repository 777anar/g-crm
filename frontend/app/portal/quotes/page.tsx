"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { listPortalQuotes } from "@/lib/api/portal";
import type { PortalQuote } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { QuoteStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { formatDate } from "@/lib/format";

export default function PortalQuotesPage() {
  const t = useTranslations("portal");
  const tCommon = useTranslations("common");
  const [quotes, setQuotes] = useState<PortalQuote[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const reload = useCallback(async (options: { append?: boolean; cursor?: string } = {}) => {
    const res = await listPortalQuotes({ cursor: options.cursor });
    setQuotes((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
    setNextCursor(res.next_cursor);
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  function handleLoadMore() {
    if (nextCursor) reload({ append: true, cursor: nextCursor });
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("nav.quotes")}</h1>
      </div>

      {quotes === null && <TableSkeleton rows={4} columns={4} />}
      {quotes && quotes.length === 0 && <EmptyState title={t("noQuotesYet")} description={t("noQuotesDesc")} />}

      {quotes && quotes.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("quoteNumber")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-4 py-2 font-medium">{t("total")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((quote) => (
                  <tr key={quote.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-mono text-text-primary">
                      <Link href={`/portal/quotes/${quote.id}`} className="hover:text-primary hover:underline">
                        {quote.quote_number}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      <QuoteStatusBadge status={quote.status} />
                    </td>
                    <td className="px-4 py-2 text-text-primary">
                      {quote.currency} {parseFloat(quote.total_final).toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{formatDate(quote.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={handleLoadMore}>
                {tCommon("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
