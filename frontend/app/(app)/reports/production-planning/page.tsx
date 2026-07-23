"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { getProductionPlanning } from "@/lib/api/reports";
import { updateWorkOrderStage } from "@/lib/api/production";
import type { ProductionPlanning } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { WorkOrderPriorityBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { usePermission } from "@/lib/permissions";
import { useToast } from "@/components/ui/toast";

const UNASSIGNED_COLUMN = "__unassigned__";

export default function ProductionPlanningDashboardPage() {
  const t = useTranslations("reports");
  const router = useRouter();
  const toast = useToast();
  const canMoveStage = usePermission("production:stage:write");

  const [data, setData] = useState<ProductionPlanning | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [moving, setMoving] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkTargetStage, setBulkTargetStage] = useState<string>(UNASSIGNED_COLUMN);

  function reload() {
    getProductionPlanning()
      .then(setData)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  function toggleSelect(jobId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) next.delete(jobId);
      else next.add(jobId);
      return next;
    });
  }

  async function moveJobsToStage(jobIds: string[], columnId: string) {
    const stageId = columnId === UNASSIGNED_COLUMN ? null : columnId;
    setMoving(true);
    try {
      const results = await Promise.allSettled(jobIds.map((id) => updateWorkOrderStage(id, stageId)));
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed > 0) {
        toast.error(t("stageMovePartialFailure", { succeeded: jobIds.length - failed, count: jobIds.length }));
      }
      setSelected(new Set());
      reload();
    } finally {
      setMoving(false);
    }
  }

  function handleDragStart(e: React.DragEvent, jobId: string) {
    e.dataTransfer.setData("text/plain", jobId);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDrop(e: React.DragEvent, columnId: string) {
    e.preventDefault();
    setDragOverColumn(null);
    const jobId = e.dataTransfer.getData("text/plain");
    if (!jobId) return;
    moveJobsToStage([jobId], columnId);
  }

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

      {canMoveStage && selected.size > 0 && (
        <Card className="flex flex-wrap items-end gap-3 border-primary/30 bg-primary/5">
          <p className="text-sm font-medium text-text-primary">{t("jobsSelected", { count: selected.size })}</p>
          <select
            value={bulkTargetStage}
            onChange={(e) => setBulkTargetStage(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value={UNASSIGNED_COLUMN}>{t("noStageColumn")}</option>
            {data.stages.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <Button loading={moving} onClick={() => moveJobsToStage(Array.from(selected), bulkTargetStage)}>
            {t("moveSelectedToStage")}
          </Button>
          <Button variant="secondary" onClick={() => setSelected(new Set())}>
            {t("clearSelection")}
          </Button>
        </Card>
      )}

      {canMoveStage && <p className="text-xs text-text-secondary">{t("dragDropHint")}</p>}

      <div className="overflow-x-auto">
        <div className="flex gap-3" style={{ minWidth: `${columns.length * 260}px` }}>
          {columns.map((col) => (
            <div
              key={col.id}
              className={`flex w-64 flex-shrink-0 flex-col gap-2 rounded-md ${dragOverColumn === col.id ? "bg-primary/5 outline outline-2 outline-dashed outline-primary/40" : ""}`}
              onDragOver={(e) => {
                if (!canMoveStage) return;
                e.preventDefault();
                setDragOverColumn(col.id);
              }}
              onDragLeave={() => setDragOverColumn((current) => (current === col.id ? null : current))}
              onDrop={(e) => (canMoveStage ? handleDrop(e, col.id) : undefined)}
            >
              <div className="flex items-center justify-between px-1">
                <h3 className="text-sm font-semibold text-text-primary">{col.name}</h3>
                <span className="text-xs text-text-secondary">{col.jobs.length}</span>
              </div>
              <div className="flex flex-col gap-2">
                {col.jobs.map((job) => (
                  <div
                    key={job.id}
                    draggable={canMoveStage}
                    onDragStart={(e) => handleDragStart(e, job.id)}
                    className={`cursor-pointer rounded-lg border border-border bg-surface p-4 ${job.is_overdue ? "border-t-2 border-t-danger" : "border-t-2 border-t-border"}`}
                  >
                    <div className="flex items-start gap-2">
                      {canMoveStage && (
                        <input
                          type="checkbox"
                          className="mt-0.5"
                          aria-label={t("selectJob", { number: job.work_order_number })}
                          checked={selected.has(job.id)}
                          onChange={() => toggleSelect(job.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                      <div className="flex-1" onClick={() => router.push(`/production/${job.id}`)}>
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
                    </div>
                  </div>
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
