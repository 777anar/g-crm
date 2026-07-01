"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { getProject, updateProject, listQuotes, createQuote } from "@/lib/api/sales";
import type { Project, Quote } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("sales");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [project, setProject] = useState<Project | null>(null);
  const [quotes, setQuotes] = useState<Quote[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    Promise.all([getProject(id), listQuotes(id)])
      .then(([proj, qs]) => {
        setProject(proj);
        setQuotes(qs.items);
      })
      .finally(() => setLoading(false));
  }, [id]);

  async function handleNewQuote() {
    setCreating(true);
    try {
      const q = await createQuote(id);
      router.push(`/sales/projects/${id}/quotes/${q.id}`);
    } finally {
      setCreating(false);
    }
  }

  function statusColor(status: string) {
    const map: Record<string, string> = {
      draft: "status-draft",
      sent: "status-sent",
      negotiation: "status-negotiation",
      accepted: "status-accepted",
      rejected: "status-rejected",
      expired: "status-expired",
    };
    return map[status] ?? "";
  }

  if (loading) return <TableSkeleton />;
  if (!project) return <div className="page-container">{tCommon("notFound")}</div>;

  return (
    <div className="page-container">
      <div className="mb-4">
        <Link href="/sales/projects" className="back-link">← {t("backToProjects")}</Link>
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">{project.name}</h1>
          <p className="page-subtitle">
            {t(`projectType_${project.project_type || "other"}` as any)}
            {project.address ? ` · ${project.address}` : ""}
          </p>
        </div>
        <Button onClick={handleNewQuote} disabled={creating}>
          {creating ? t("creating") : t("createQuote")}
        </Button>
      </div>

      <div className="section-title mt-6 mb-3">{t("quotesTitle")}</div>

      {quotes === null ? (
        <TableSkeleton />
      ) : quotes.length === 0 ? (
        <EmptyState title={t("noQuotesYet")} description="" />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("tableQuoteNum")}</th>
                <th>{t("quoteVersion")}</th>
                <th>{t("quoteStatus")}</th>
                <th>{t("tableTotal")}</th>
                <th>{t("validUntil")}</th>
                <th>{t("tableCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => (
                <tr
                  key={q.id}
                  className="clickable-row"
                  onClick={() => router.push(`/sales/projects/${id}/quotes/${q.id}`)}
                >
                  <td className="font-medium font-mono">{q.quote_number}</td>
                  <td>v{q.version}</td>
                  <td>
                    <span className={`status-badge ${statusColor(q.status)}`}>
                      {t(q.status as any)}
                    </span>
                  </td>
                  <td>{q.currency} {parseFloat(q.total_final).toFixed(2)}</td>
                  <td>{q.valid_until ? new Date(q.valid_until).toLocaleDateString() : tCommon("dash")}</td>
                  <td>{new Date(q.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
