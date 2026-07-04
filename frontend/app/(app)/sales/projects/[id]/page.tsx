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
import { ProjectStatusBadge, QuoteStatusBadge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";

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

  if (loading) return <TableSkeleton rows={5} columns={5} />;
  if (!project) return <p className="text-sm text-text-secondary">{tCommon("notFound")}</p>;

  return (
    <div className="flex flex-col gap-4">
      <Link href="/sales/projects" className="text-sm text-primary hover:underline">
        ← {t("backToProjects")}
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{project.name}</h1>
          <p className="text-sm text-text-secondary">
            {t(`projectType_${project.project_type || "other"}` as any)}
            {project.address ? ` · ${project.address}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ProjectStatusBadge status={project.status} />
          <Button onClick={handleNewQuote} disabled={creating}>
            {creating ? t("creating") : t("createQuote")}
          </Button>
        </div>
      </div>

      <h2 className="text-lg font-semibold text-text-primary">{t("quotesTitle")}</h2>

      {quotes === null && <TableSkeleton rows={4} columns={5} />}

      {quotes && quotes.length === 0 && <EmptyState title={t("noQuotesYet")} />}

      {quotes && quotes.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("tableQuoteNum")}</th>
                <th className="px-4 py-2 font-medium">{t("quoteVersion")}</th>
                <th className="px-4 py-2 font-medium">{t("quoteStatus")}</th>
                <th className="px-4 py-2 font-medium">{t("tableTotal")}</th>
                <th className="px-4 py-2 font-medium">{t("validUntil")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => (
                <tr
                  key={q.id}
                  onClick={() => router.push(`/sales/projects/${id}/quotes/${q.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  <td className="px-4 py-2 font-mono font-medium text-text-primary">{q.quote_number}</td>
                  <td className="px-4 py-2 text-text-secondary">v{q.version}</td>
                  <td className="px-4 py-2">
                    <QuoteStatusBadge status={q.status} />
                  </td>
                  <td className="px-4 py-2 text-text-primary">{q.currency} {parseFloat(q.total_final).toFixed(2)}</td>
                  <td className="px-4 py-2 text-text-secondary">{q.valid_until ? formatDate(q.valid_until) : tCommon("dash")}</td>
                  <td className="px-4 py-2 text-text-secondary">{formatDate(q.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
