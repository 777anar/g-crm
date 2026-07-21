"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getPortalDocumentDownloadUrl, listPortalDocuments } from "@/lib/api/portal";
import type { PortalDocument } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { formatDate } from "@/lib/format";

export default function PortalDocumentsPage() {
  const t = useTranslations("portal");
  const tCommon = useTranslations("common");
  const [documents, setDocuments] = useState<PortalDocument[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const reload = useCallback(async (options: { append?: boolean; cursor?: string } = {}) => {
    const res = await listPortalDocuments({ cursor: options.cursor });
    setDocuments((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
    setNextCursor(res.next_cursor);
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  function handleLoadMore() {
    if (nextCursor) reload({ append: true, cursor: nextCursor });
  }

  async function handleDownload(id: string) {
    setDownloadingId(id);
    try {
      const { url } = await getPortalDocumentDownloadUrl(id);
      window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("nav.documents")}</h1>
      </div>

      {documents === null && <TableSkeleton rows={4} columns={3} />}
      {documents && documents.length === 0 && (
        <EmptyState title={t("noDocumentsYet")} description={t("noDocumentsDesc")} />
      )}

      {documents && documents.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("documentType")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 text-text-primary">
                      {doc.related_entity_type === "customer" ? t("documentTypeContract") : t("documentTypeInstallation")}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{formatDate(doc.created_at)}</td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        variant="secondary"
                        loading={downloadingId === doc.id}
                        onClick={() => handleDownload(doc.id)}
                      >
                        {t("download")}
                      </Button>
                    </td>
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
