"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  assignWorkOrderOperator,
  getProductionJob,
  getWorkOrderTimeline,
  listProductionStages,
  updateWorkOrder,
  updateWorkOrderPriority,
  updateWorkOrderStage,
  updateWorkOrderStatus,
} from "@/lib/api/production";
import { listCompanyUsers } from "@/lib/api/companies";
import type { CompanyUser, ProductionJob, ProductionStage, WorkOrderEvent, WorkOrderPriority } from "@/lib/types";
import { WORK_ORDER_PRIORITIES } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { WorkOrderPriorityBadge, WorkOrderStatusBadge } from "@/components/ui/badge";
import { SelectField, TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate, formatDateTime } from "@/lib/format";

const NEXT_STATUS: Record<string, string | null> = {
  queued: "cutting",
  cutting: "polishing",
  polishing: "quality_check",
  quality_check: "completed",
  completed: null,
  cancelled: null,
};

export default function ProductionJobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("production");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const toast = useToast();

  const [job, setJob] = useState<ProductionJob | null>(null);
  const [timeline, setTimeline] = useState<WorkOrderEvent[] | null>(null);
  const [stages, setStages] = useState<ProductionStage[]>([]);
  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [savingField, setSavingField] = useState<string | null>(null);
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");

  const reload = useCallback(async () => {
    const [jobRes, timelineRes] = await Promise.all([getProductionJob(id), getWorkOrderTimeline(id)]);
    setJob(jobRes);
    setTimeline(timelineRes.items);
    setDueDate(jobRes.due_date ?? "");
    setNotes(jobRes.notes ?? "");
    setLoading(false);
  }, [id]);

  useEffect(() => {
    reload();
    listProductionStages().then((r) => setStages(r.items)).catch(() => {});
    listCompanyUsers().then(setUsers).catch(() => {});
  }, [reload]);

  async function handleAdvance() {
    if (!job) return;
    const next = NEXT_STATUS[job.status];
    if (!next) return;
    setTransitioning(true);
    try {
      await updateWorkOrderStatus(id, next);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleCancel() {
    setTransitioning(true);
    try {
      await updateWorkOrderStatus(id, "cancelled", cancelReason || undefined);
      setCancelMode(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handlePriorityChange(priority: string) {
    setSavingField("priority");
    try {
      await updateWorkOrderPriority(id, priority);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setSavingField(null);
    }
  }

  async function handleOperatorChange(operatorUserId: string) {
    setSavingField("operator");
    try {
      await assignWorkOrderOperator(id, operatorUserId || null);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setSavingField(null);
    }
  }

  async function handleStageChange(stageId: string) {
    setSavingField("stage");
    try {
      await updateWorkOrderStage(id, stageId || null);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setSavingField(null);
    }
  }

  async function handleSaveDueDateAndNotes() {
    setSavingField("details");
    try {
      await updateWorkOrder(id, { due_date: dueDate || undefined, notes });
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setSavingField(null);
    }
  }

  if (loading || !job) return <TableSkeleton rows={5} columns={4} />;

  const isTerminal = job.status === "completed" || job.status === "cancelled";
  const nextStatus = NEXT_STATUS[job.status];

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("production"), href: "/production" }, { label: job.work_order_number }]} />

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-text-primary">{job.work_order_number}</h1>
            <WorkOrderStatusBadge status={job.status} />
            <WorkOrderPriorityBadge priority={job.priority} />
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            {t("forOrder")}:{" "}
            <Link href={`/orders/${job.order.id}`} className="text-primary hover:underline">
              {job.order.name}
            </Link>
          </p>
        </div>
        {!isTerminal && (
          <div className="flex gap-2">
            {nextStatus && (
              <Button onClick={handleAdvance} disabled={transitioning}>
                {transitioning ? t("saving") : `→ ${t(nextStatus as Parameters<typeof t>[0])}`}
              </Button>
            )}
            {!cancelMode && (
              <Button variant="secondary" onClick={() => setCancelMode(true)}>
                {t("markCancelled")}
              </Button>
            )}
          </div>
        )}
      </div>

      {cancelMode && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="mb-2 text-sm font-medium text-danger">{t("cancelReason")}</p>
          <textarea
            className="mb-2 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            rows={2}
            aria-label={t("cancelReason")}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <div className="flex gap-2">
            <Button onClick={handleCancel} disabled={transitioning}>{t("cancelWorkOrder")}</Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      {job.cancelled_reason && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="text-sm text-danger">{t("cancelReason")}: {job.cancelled_reason}</p>
        </Card>
      )}

      <Card>
        <CardHeader title={t("jobDetails")} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-sm text-text-secondary">{t("customer")}</dt>
            <dd className="mt-1 text-sm text-text-primary">
              <Link href={`/crm/customers/${job.customer.id}`} className="text-primary hover:underline">
                {job.customer.name}
              </Link>
            </dd>
          </div>
          <div>
            <dt className="text-sm text-text-secondary">{t("project")}</dt>
            <dd className="mt-1 text-sm text-text-primary">
              <Link href={`/sales/projects/${job.project.id}`} className="text-primary hover:underline">
                {job.project.name}
              </Link>
            </dd>
          </div>
          <SelectField
            label={t("priority")}
            value={job.priority}
            disabled={savingField === "priority" || isTerminal}
            onChange={(e) => handlePriorityChange(e.target.value)}
          >
            {WORK_ORDER_PRIORITIES.map((p: WorkOrderPriority) => (
              <option key={p} value={p}>
                {t(`priority_${p}` as Parameters<typeof t>[0])}
              </option>
            ))}
          </SelectField>
          <SelectField
            label={t("assignedOperator")}
            value={job.assigned_operator ?? ""}
            disabled={savingField === "operator" || isTerminal}
            onChange={(e) => handleOperatorChange(e.target.value)}
          >
            <option value="">{t("unassigned")}</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </SelectField>
          <SelectField
            label={t("currentStage")}
            value={job.current_stage?.id ?? ""}
            disabled={savingField === "stage" || isTerminal}
            onChange={(e) => handleStageChange(e.target.value)}
          >
            <option value="">{t("noStage")}</option>
            {stages.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </SelectField>
          <TextField
            label={t("dueDate")}
            type="date"
            value={dueDate}
            disabled={isTerminal}
            onChange={(e) => setDueDate(e.target.value)}
          />
        </div>
        <div className="mt-4">
          <TextField
            label={t("notes")}
            value={notes}
            disabled={isTerminal}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>
        {!isTerminal && (
          <div className="mt-3 flex justify-end">
            <Button variant="secondary" loading={savingField === "details"} onClick={handleSaveDueDateAndNotes}>
              {tCommon("save")}
            </Button>
          </div>
        )}
      </Card>

      <Card className="p-0 overflow-hidden">
        <div className="border-b border-border bg-bg px-4 py-2 text-sm font-medium text-text-secondary">
          {t("slabsConsumed")}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("slabNumber")}</th>
                <th className="px-4 py-2 font-medium">{t("description")}</th>
                <th className="px-4 py-2 font-medium">{t("material")}</th>
                <th className="px-4 py-2 font-medium">{t("thickness")}</th>
                <th className="px-4 py-2 font-medium">{t("finish")}</th>
                <th className="px-4 py-2 font-medium">{t("quantity")}</th>
                <th className="px-4 py-2 font-medium">{t("slabArea")}</th>
              </tr>
            </thead>
            <tbody>
              {job.items.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="px-4 py-2 font-mono text-text-primary">{item.slab_number}</td>
                  <td className="px-4 py-2">{item.description}</td>
                  <td className="px-4 py-2 text-text-secondary">{item.material_name}</td>
                  <td className="px-4 py-2 text-text-secondary">{item.thickness_mm ? `${item.thickness_mm} mm` : tCommon("dash")}</td>
                  <td className="px-4 py-2 text-text-secondary">{item.finish ?? tCommon("dash")}</td>
                  <td className="px-4 py-2 text-text-secondary">{item.quantity} {item.unit}</td>
                  <td className="px-4 py-2 text-text-secondary">
                    {item.area_m2 ? `${parseFloat(item.area_m2).toFixed(2)} m²` : tCommon("dash")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardHeader title={t("timeline")} />
        {timeline && timeline.length > 0 ? (
          <ol className="flex flex-col gap-3">
            {timeline.map((event) => (
              <li key={event.id} className="flex gap-3 border-l-2 border-border pl-3">
                <div className="flex-1">
                  <p className="text-sm text-text-primary">
                    {event.event_type === "stage_changed" && !event.from_value
                      ? t("timelineEvent_stage_set", { to: event.to_value ?? tCommon("dash") })
                      : t(`timelineEvent_${event.event_type}` as Parameters<typeof t>[0], {
                          from: event.from_value ?? tCommon("dash"),
                          to: event.to_value ?? tCommon("dash"),
                        })}
                  </p>
                  {event.notes && <p className="text-xs text-text-secondary">{event.notes}</p>}
                  <p className="text-xs text-text-secondary">
                    {formatDateTime(event.changed_at ?? event.created_at)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-text-secondary">{t("noTimelineEvents")}</p>
        )}
      </Card>

      <p className="text-xs text-text-secondary">
        {t("created")}: {formatDate(job.created_at)}
        {job.completed_at && ` · ${t("completed")}: ${formatDate(job.completed_at)}`}
      </p>
    </div>
  );
}
