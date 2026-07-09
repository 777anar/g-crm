"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  getOrder,
  listOrderSections,
  listSectionItems,
  listSectionMeasurements,
  updateOrder,
  updateOrderStatus,
  updateOrderItem,
} from "@/lib/api/orders";
import { createWorkOrder, getWorkOrderForOrder } from "@/lib/api/production";
import { createInstallationJob, getInstallationJobForOrder } from "@/lib/api/installation";
import { createInvoice, getInvoiceForOrder } from "@/lib/api/finance";
import type { Order, OrderItem, OrderMeasurement, OrderSection, WorkOrder, InstallationJob, Invoice } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { OrderStatusBadge, WorkOrderStatusBadge, InstallationJobStatusBadge, InvoiceStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";

type SectionData = {
  section: OrderSection;
  items: OrderItem[];
  measurements: OrderMeasurement[];
};

const NEXT_STATUS: Record<string, string | null> = {
  waiting: "approved_for_production",
  measuring: "approved_for_production",
  approved_for_production: "in_production",
  in_production: "ready",
  ready: "delivered",
  delivered: "installed",
  installed: "completed",
  completed: null,
  cancelled: null,
};

// Includes "queued"/"quality_check" so items already carrying a value set by
// the Production module's work order lifecycle (see modules/production)
// show a real label here too, not just items edited from this dropdown.
const PROD_STATUSES = ["pending", "queued", "cutting", "polishing", "quality_check", "done"];
// Mirrors the Installation module's own job status vocabulary (see
// modules/installation), which is what actually writes this field once a
// job exists -- kept here so an item's current value always has a label.
const INST_STATUSES = ["pending", "scheduled", "en_route", "in_progress", "done"];

const inputClasses =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary";

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("orders");
  const tSales = useTranslations("sales");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const toast = useToast();

  const [order, setOrder] = useState<Order | null>(null);
  const [sectionData, setSectionData] = useState<SectionData[] | null>(null);
  const [workOrder, setWorkOrder] = useState<WorkOrder | null>(null);
  const [installationJob, setInstallationJob] = useState<InstallationJob | null>(null);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [creatingWorkOrder, setCreatingWorkOrder] = useState(false);
  const [creatingInstallationJob, setCreatingInstallationJob] = useState(false);
  const [creatingInvoice, setCreatingInvoice] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({
    notes: "",
    production_notes: "",
    installation_notes: "",
    delivery_address: "",
    scheduled_production_date: "",
    scheduled_installation_date: "",
  });

  const reload = useCallback(async () => {
    const o = await getOrder(id);
    setOrder(o);
    setForm({
      notes: o.notes ?? "",
      production_notes: o.production_notes ?? "",
      installation_notes: o.installation_notes ?? "",
      delivery_address: o.delivery_address ?? "",
      scheduled_production_date: o.scheduled_production_date ?? "",
      scheduled_installation_date: o.scheduled_installation_date ?? "",
    });
    const secs = await listOrderSections(id);
    const enriched = await Promise.all(
      secs.items.map(async (s) => {
        const [itemsRes, meaRes] = await Promise.all([
          listSectionItems(id, s.id),
          listSectionMeasurements(id, s.id),
        ]);
        return { section: s, items: itemsRes.items, measurements: meaRes.items };
      })
    );
    setSectionData(enriched);

    try {
      setWorkOrder(await getWorkOrderForOrder(id));
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 404) {
        setWorkOrder(null);
      } else {
        throw err;
      }
    }

    try {
      setInstallationJob(await getInstallationJobForOrder(id));
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 404) {
        setInstallationJob(null);
      } else {
        throw err;
      }
    }

    try {
      setInvoice(await getInvoiceForOrder(id));
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 404) {
        setInvoice(null);
      } else {
        throw err;
      }
    }

    setLoading(false);
  }, [id]);

  useEffect(() => { reload(); }, [reload]);

  async function handleCreateWorkOrder() {
    setCreatingWorkOrder(true);
    try {
      await createWorkOrder(id);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setCreatingWorkOrder(false);
    }
  }

  async function handleCreateInstallationJob() {
    setCreatingInstallationJob(true);
    try {
      await createInstallationJob(id);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setCreatingInstallationJob(false);
    }
  }

  async function handleCreateInvoice() {
    setCreatingInvoice(true);
    try {
      await createInvoice(id);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setCreatingInvoice(false);
    }
  }

  async function handleAdvance() {
    if (!order) return;
    const next = NEXT_STATUS[order.status];
    if (!next) return;
    setTransitioning(true);
    try {
      await updateOrderStatus(id, next);
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
      await updateOrderStatus(id, "cancelled", cancelReason || undefined);
      setCancelMode(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleSaveDetails() {
    try {
      await updateOrder(id, {
        notes: form.notes || null,
        production_notes: form.production_notes || null,
        installation_notes: form.installation_notes || null,
        delivery_address: form.delivery_address || null,
        scheduled_production_date: form.scheduled_production_date || null,
        scheduled_installation_date: form.scheduled_installation_date || null,
      });
      setEditMode(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  async function handleItemStatusChange(
    itemId: string,
    field: "production_status" | "installation_status",
    value: string
  ) {
    try {
      await updateOrderItem(id, itemId, { [field]: value || null });
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  if (loading || !order) return <TableSkeleton rows={5} columns={5} />;

  const isTerminal = order.status === "completed" || order.status === "cancelled";
  const nextStatus = NEXT_STATUS[order.status];

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("orders"), href: "/orders" }, { label: order.order_number }]} />

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-text-primary">{order.order_number}</h1>
            <OrderStatusBadge status={order.status} />
          </div>
          <p className="mt-1 text-xs text-text-secondary">{t("fromQuote")}: {order.quote_id}</p>
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
            className={`${inputClasses} mb-2 w-full`}
            rows={2}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <div className="flex gap-2">
            <Button onClick={handleCancel} disabled={transitioning}>{t("cancelOrder")}</Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      {/* Work order */}
      {workOrder ? (
        <Card className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary">{t("workOrder")}:</span>
            <span className="font-mono text-sm font-medium text-text-primary">{workOrder.work_order_number}</span>
            <WorkOrderStatusBadge status={workOrder.status} />
          </div>
          <Link href={`/production/${workOrder.id}`} className="text-sm text-primary hover:underline">
            {t("viewWorkOrder")} →
          </Link>
        </Card>
      ) : order.status === "approved_for_production" ? (
        <Card className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">{t("noWorkOrderYet")}</p>
          <Button onClick={handleCreateWorkOrder} disabled={creatingWorkOrder}>
            {creatingWorkOrder ? t("saving") : t("createWorkOrder")}
          </Button>
        </Card>
      ) : null}

      {/* Installation job */}
      {installationJob ? (
        <Card className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary">{t("installationJob")}:</span>
            <span className="font-mono text-sm font-medium text-text-primary">{installationJob.job_number}</span>
            <InstallationJobStatusBadge status={installationJob.status} />
          </div>
          <Link href={`/installation/jobs/${installationJob.id}`} className="text-sm text-primary hover:underline">
            {t("viewInstallationJob")} →
          </Link>
        </Card>
      ) : order.status === "ready" || order.status === "delivered" ? (
        <Card className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">{t("noInstallationJobYet")}</p>
          <Button onClick={handleCreateInstallationJob} disabled={creatingInstallationJob}>
            {creatingInstallationJob ? t("saving") : t("createInstallationJob")}
          </Button>
        </Card>
      ) : null}

      {/* Invoice */}
      {invoice ? (
        <Card className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary">{t("invoice")}:</span>
            <span className="font-mono text-sm font-medium text-text-primary">{invoice.invoice_number}</span>
            <InvoiceStatusBadge status={invoice.status} />
          </div>
          <Link href={`/finance/invoices/${invoice.id}`} className="text-sm text-primary hover:underline">
            {t("viewInvoice")} →
          </Link>
        </Card>
      ) : ["ready", "delivered", "installed", "completed"].includes(order.status) ? (
        <Card className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">{t("noInvoiceYet")}</p>
          <Button onClick={handleCreateInvoice} disabled={creatingInvoice}>
            {creatingInvoice ? t("saving") : t("createInvoice")}
          </Button>
        </Card>
      ) : null}

      {/* Totals bar */}
      <Card className="flex flex-wrap gap-6 text-sm">
        <div><span className="text-text-secondary">{t("subtotal")}:</span> <strong className="text-text-primary">{order.currency} {parseFloat(order.subtotal_gross).toFixed(2)}</strong></div>
        {parseFloat(order.discount_amount) > 0 && (
          <div><span className="text-text-secondary">{t("discount")}:</span> <strong className="text-text-primary">− {order.currency} {parseFloat(order.discount_amount).toFixed(2)}</strong></div>
        )}
        <div><span className="text-text-secondary">{t("vat")} {order.vat_rate}%:</span> <strong className="text-text-primary">{order.currency} {parseFloat(order.vat_amount).toFixed(2)}</strong></div>
        <div className="ml-auto text-base"><span className="text-text-secondary">{t("totalFinal")}:</span> <strong className="text-lg text-primary">{order.currency} {parseFloat(order.total_final).toFixed(2)}</strong></div>
      </Card>

      {/* Details card */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text-primary">{t("notes")}</h2>
          {!isTerminal && (
            <button
              className="text-xs text-primary hover:underline"
              onClick={() => (editMode ? handleSaveDetails() : setEditMode(true))}
            >
              {editMode ? tCommon("save") : tCommon("edit")}
            </button>
          )}
        </div>
        {editMode ? (
          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            {(
              [
                ["notes", t("notes")],
                ["production_notes", t("productionNotes")],
                ["installation_notes", t("installationNotes")],
                ["delivery_address", t("deliveryAddress")],
                ["scheduled_production_date", t("scheduledProduction")],
                ["scheduled_installation_date", t("scheduledInstallation")],
              ] as [keyof typeof form, string][]
            ).map(([key, label]) => (
              <div key={key}>
                <label className="text-xs text-text-secondary">{label}</label>
                <input
                  className={`${inputClasses} mt-0.5 w-full`}
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                />
              </div>
            ))}
          </div>
        ) : (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {[
              [t("notes"), order.notes],
              [t("productionNotes"), order.production_notes],
              [t("installationNotes"), order.installation_notes],
              [t("deliveryAddress"), order.delivery_address],
              [t("scheduledProduction"), order.scheduled_production_date],
              [t("scheduledInstallation"), order.scheduled_installation_date],
            ].map(([label, val]) => (
              <div key={label as string}>
                <dt className="text-xs text-text-secondary">{label}</dt>
                <dd className="text-text-primary">{val ?? tCommon("dash")}</dd>
              </div>
            ))}
          </dl>
        )}
      </Card>

      {/* Sections */}
      {sectionData?.map(({ section, items, measurements }) => (
        <Card key={section.id} className="p-0 overflow-hidden">
          <div className="flex items-center justify-between bg-text-primary px-4 py-3 text-white">
            <h2 className="font-semibold">{section.name}</h2>
            <span className="text-sm">{order.currency} {parseFloat(section.subtotal_sale).toFixed(2)}</span>
          </div>

          {measurements.length > 0 && (
            <div className="border-b border-border bg-bg p-3 text-sm">
              <p className="mb-2 text-xs font-medium text-text-secondary">{t("measurements")}</p>
              <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-text-secondary">
                  <tr>
                    <th className="px-2 py-1 font-medium">{t("label")}</th>
                    <th className="px-2 py-1 font-medium">{t("lengthMm")}</th>
                    <th className="px-2 py-1 font-medium">{t("widthMm")}</th>
                    <th className="px-2 py-1 font-medium">{t("quantity")}</th>
                    <th className="px-2 py-1 font-medium">{t("areaSqm")}</th>
                    <th className="px-2 py-1 font-medium">{t("requiredArea")}</th>
                  </tr>
                </thead>
                <tbody>
                  {measurements.map((m) => (
                    <tr key={m.id} className="border-t border-border">
                      <td className="px-2 py-1">{m.label ?? "—"}</td>
                      <td className="px-2 py-1">{m.length_mm ?? "—"}</td>
                      <td className="px-2 py-1">{m.width_mm ?? "—"}</td>
                      <td className="px-2 py-1">{m.quantity}</td>
                      <td className="px-2 py-1">{m.area_m2 ? parseFloat(m.area_m2).toFixed(3) : "—"}</td>
                      <td className="px-2 py-1">{m.required_area_m2 ? parseFloat(m.required_area_m2).toFixed(3) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          )}

          {items.length > 0 && (
            <div className="p-3">
              <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-text-secondary">
                  <tr>
                    <th className="px-2 py-1 font-medium">{t("productionStatus")}</th>
                    <th className="px-2 py-1 font-medium">{t("installationStatus")}</th>
                    <th className="px-2 py-1 font-medium">{t("itemType")}</th>
                    <th className="px-2 py-1 font-medium">{t("description")}</th>
                    <th className="px-2 py-1 font-medium">{t("quantity")}</th>
                    <th className="px-2 py-1 font-medium">{t("unit")}</th>
                    <th className="px-2 py-1 font-medium">{t("unitPrice")}</th>
                    <th className="px-2 py-1 font-medium">{t("total")}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-border">
                      <td className="px-2 py-1">
                        <select
                          className={inputClasses}
                          value={item.production_status ?? ""}
                          onChange={(e) => handleItemStatusChange(item.id, "production_status", e.target.value)}
                          disabled={isTerminal || workOrder !== null}
                        >
                          <option value="">—</option>
                          {PROD_STATUSES.map((s) => (
                            <option key={s} value={s}>{t(`prodStatus_${s}` as any)}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-2 py-1">
                        <select
                          className={inputClasses}
                          value={item.installation_status ?? ""}
                          onChange={(e) => handleItemStatusChange(item.id, "installation_status", e.target.value)}
                          disabled={isTerminal || installationJob !== null}
                        >
                          <option value="">—</option>
                          {INST_STATUSES.map((s) => (
                            <option key={s} value={s}>{t(`instStatus_${s}` as any)}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-2 py-1 text-xs text-text-secondary">{tSales(`itemType_${item.item_type}` as any)}</td>
                      <td className="px-2 py-1">{item.description || "—"}</td>
                      <td className="px-2 py-1">{item.quantity}</td>
                      <td className="px-2 py-1">{item.unit}</td>
                      <td className="px-2 py-1">{parseFloat(item.unit_sale_price).toFixed(2)}</td>
                      <td className="px-2 py-1 font-medium text-text-primary">{parseFloat(item.line_total_sale).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
