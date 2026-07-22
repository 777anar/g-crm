"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listCutOptimizationRuns } from "@/lib/api/cut-optimization";
import type { CutOptimizationRun } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";

export default function CutOptimizationHistoryPage() {
  const t = useTranslations("cutOptimization");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const router = useRouter();

  const [runs, setRuns] = useState<CutOptimizationRun[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((options: { append?: boolean; cursor?: string } = {}) => {
    listCutOptimizationRuns({ cursor: options.cursor })
      .then((r) => {
        setRuns((prev) => (options.append && prev ? [...prev, ...r.items] : r.items));
        setNextCursor(r.next_cursor);
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("cutOptimization"), href: "/cut-optimization" }, { label: t("historyLink") }]} />

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("historyTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("historySubtitle")}</p>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {runs === null && !error && <TableSkeleton rows={6} columns={5} />}

      {runs && runs.length === 0 && (
        <EmptyState title={t("noRunsYet")} description={t("noRunsDesc")} />
      )}

      {runs && runs.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("tableSlab")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableSource")}</th>
                  <th className="px-4 py-2 font-medium">{t("utilization")}</th>
                  <th className="px-4 py-2 font-medium">{t("wasteArea")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    onClick={() => router.push(`/cut-optimization/history/${run.id}`)}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                  >
                    <td className="px-4 py-2 font-mono text-text-primary">{run.slab_length_mm}×{run.slab_width_mm}mm</td>
                    <td className="px-4 py-2">
                      <Badge tone={run.source === "offcut_recommendation" ? "info" : "neutral"}>
                        {t(`source_${run.source}` as any)}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{run.utilization_pct}%</td>
                    <td className="px-4 py-2 text-text-secondary">{run.waste_area_m2} m²</td>
                    <td className="px-4 py-2 text-text-secondary">{formatDateTime(run.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={() => load({ append: true, cursor: nextCursor })}>
                {tCommon("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
