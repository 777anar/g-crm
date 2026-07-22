"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { getProductionPlanning } from "@/lib/api/reports";
import type { ProductionPlanning } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { WorkOrderPriorityBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";

const UNASSIGNED_COLUMN = "__unassigned__";

export default function ProductionPlanningDashboardPage() {
  const t = useTranslations("reports");
  const router = useRouter();

  const [data, setData] = useState<ProductionPlanning | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProductionPlanning()
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  const columns = useMemo(() => {
    if (!data) return [];
    const byStage: Record<string, typeof data.jobs> = { [UNASSIGNED_COLUMN]: [] };
    for (const stage of data.stages) byStage[stage.id] = [];
    for (const job of data.jobs) {
      const key = job.stage_id ?? UNASSIGNED_COLUMN;
      (byStage[key] ??= []).push(job);
    }
    return [
      { id: UNASSIGNED_COLUMN, name: t("noStageColumn"), jobs: byStage[UNASSIGNED_COLUMN] },
      ...data.stages.map((s) => ({ id: s.id, name: s.name, jobs: byStage[s.id] ?? [] })),
    ];
  }, [data, t]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!data) return <TableSkeleton rows={5} columns={6} />;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-text-secondary">{t("productionPlanningSubtitle")}</p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <p className="text-xs text-text-secondary">{t("totalActiveJobs")}</p>
          <p className="text-2xl font-semibold text-text-primary">{data.total_active_jobs}</p>
        </Card>
        <Card className={data.overdue_count > 0 ? "border-danger/40" : ""}>
          <p className="text-xs text-text-secondary">{t("overdueJobs")}</p>
          <p className={`text-2xl font-semibold ${data.overdue_count > 0 ? "text-danger" : "text-text-primary"}`}>
            {data.overdue_count}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-text-secondary">{t("activeStages")}</p>
          <p className="text-2xl font-semibold text-text-primary">{data.stages.length}</p>
        </Card>
        <Card>
          <p className="text-xs text-text-secondary">{t("operatorsWithWork")}</p>
          <p className="text-2xl font-semibold text-text-primary">{data.operator_workload.length}</p>
        </Card>
      </div>

      <div className="overflow-x-auto">
        <div className="flex gap-3" style={{ minWidth: `${columns.length * 260}px` }}>
          {columns.map((col) => (
            <div key={col.id} className="flex w-64 flex-shrink-0 flex-col gap-2">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-sm font-semibold text-text-primary">{col.name}</h3>
                <span className="text-xs text-text-secondary">{col.jobs.length}</span>
              </div>
              <div className="flex flex-col gap-2">
                {col.jobs.map((job) => (
                  <Card
                    key={job.id}
                    className={`cursor-pointer ${job.is_overdue ? "border-t-2 border-t-danger" : "border-t-2 border-t-border"}`}
                  >
                    <div onClick={() => router.push(`/production/${job.id}`)}>
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-mono text-xs font-medium text-text-primary">{job.work_order_number}</p>
                        <WorkOrderPriorityBadge priority={job.priority} />
                      </div>
                      <p className="mt-1 text-xs text-text-secondary">{job.customer_name ?? job.order_number}</p>
                      {job.assigned_operator_name && (
                        <p className="text-xs text-text-secondary">{job.assigned_operator_name}</p>
                      )}
                      {job.due_date && (
                        <p className={`mt-1 text-xs ${job.is_overdue ? "font-medium text-danger" : "text-text-secondary"}`}>
                          {job.is_overdue ? `${t("overdueSince")} ` : ""}{formatDate(job.due_date)}
                        </p>
                      )}
                    </div>
                  </Card>
                ))}
                {col.jobs.length === 0 && (
                  <p className="px-1 text-xs text-text-secondary">{t("noJobsInColumn")}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <Card>
        <h2 className="mb-3 text-base font-semibold text-text-primary">{t("operatorWorkload")}</h2>
        {data.operator_workload.length === 0 ? (
          <p className="text-sm text-text-secondary">{t("noOperatorsAssigned")}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {data.operator_workload.map((w) => {
              const maxCount = Math.max(...data.operator_workload.map((o) => o.job_count), 1);
              return (
                <div key={w.operator_id} className="flex items-center gap-3">
                  <p className="w-40 flex-shrink-0 truncate text-sm text-text-primary">{w.operator_name}</p>
                  <div className="h-2 flex-1 rounded-full bg-bg">
                    <div
                      className="h-2 rounded-full bg-primary"
                      style={{ width: `${(w.job_count / maxCount) * 100}%` }}
                    />
                  </div>
                  <p className="w-20 flex-shrink-0 text-right text-xs text-text-secondary">
                    {w.job_count} {w.overdue_count > 0 && <span className="text-danger">({w.overdue_count} {t("overdueAbbrev")})</span>}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
