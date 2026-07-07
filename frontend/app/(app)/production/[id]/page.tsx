"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { getWorkOrder, listWorkOrderItems, updateWorkOrderStatus } from "@/lib/api/production";
import type { WorkOrder, WorkOrderItem } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { WorkOrderStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";

const NEXT_STATUS: Record<string, string | null> = {
  queued: "cutting",
  cutting: "polishing",
  polishing: "quality_check",
  quality_check: "completed",
  completed: null,
  cancelled: null,
};

export default function WorkOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("production");
  const tCommon = useTranslations("common");
  const toast = useToast();

  const [workOrder, setWorkOrder] = useState<WorkOrder | null>(null);
  const [items, setItems] = useState<WorkOrderItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const reload = useCallback(async () => {
    const [wo, itemsRes] = await Promise.all([getWorkOrder(id), listWorkOrderItems(id)]);
    setWorkOrder(wo);
    setItems(itemsRes.items);
    setLoading(false);
  }, [id]);

  useEffect(() => { reload(); }, [reload]);

  async function handleAdvance() {
    if (!workOrder) return;
    const next = NEXT_STATUS[workOrder.status];
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

  if (loading || !workOrder) return <TableSkeleton rows={5} columns={4} />;

  const isTerminal = workOrder.status === "completed" || workOrder.status === "cancelled";
  const nextStatus = NEXT_STATUS[workOrder.status];

  return (
    <div className="flex flex-col gap-4">
      <Link href="/production" className="text-sm text-primary hover:underline">
        ← {t("backToWorkOrders")}
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-text-primary">{workOrder.work_order_number}</h1>
            <WorkOrderStatusBadge status={workOrder.status} />
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            {t("forOrder")}:{" "}
            <Link href={`/orders/${workOrder.order_id}`} className="text-primary hover:underline">
              {workOrder.order_id}
            </Link>
          </p>
        </div>
        {!isTerminal && (
          <div className="flex gap-2">
            {nextStatus && (
              <Button onClick={handleAdvance} disabled={transitioning}>
                {transitioning ? t("saving") : `→ ${t(nextStatus as any)}`}
              </Button>
            )}
            <Button variant="secondary" onClick={() => setCancelMode(!cancelMode)}>
              {t("markCancelled")}
            </Button>
          </div>
        )}
      </div>

      {cancelMode && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="mb-2 text-sm font-medium text-danger">{t("cancelReason")}</p>
          <textarea
            className="mb-2 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            rows={2}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <div className="flex gap-2">
            <Button onClick={handleCancel} disabled={transitioning}>{t("cancelWorkOrder")}</Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      {workOrder.cancelled_reason && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="text-sm text-danger">{t("cancelReason")}: {workOrder.cancelled_reason}</p>
        </Card>
      )}

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
              <th className="px-4 py-2 font-medium">{t("quantity")}</th>
              <th className="px-4 py-2 font-medium">{t("slabArea")}</th>
            </tr>
          </thead>
          <tbody>
            {items?.map((item) => (
              <tr key={item.id} className="border-t border-border">
                <td className="px-4 py-2 font-mono text-text-primary">{item.slab_number}</td>
                <td className="px-4 py-2">{item.description}</td>
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

      <p className="text-xs text-text-secondary">
        {t("created")}: {formatDate(workOrder.created_at)}
        {workOrder.completed_at && ` · ${t("completed")}: ${formatDate(workOrder.completed_at)}`}
      </p>
    </div>
  );
}
