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
import type { Order, OrderItem, OrderMeasurement, OrderSection } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { OrderStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";

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

const PROD_STATUSES = ["pending", "cutting", "polishing", "done"];
const INST_STATUSES = ["pending", "scheduled", "done"];

const inputClasses =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary";

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("orders");
  const tCommon = useTranslations("common");

  const [order, setOrder] = useState<Order | null>(null);
  const [sectionData, setSectionData] = useState<SectionData[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
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
    setLoading(false);
  }, [id]);

  useEffect(() => { reload(); }, [reload]);

  async function handleAdvance() {
    if (!order) return;
    const next = NEXT_STATUS[order.status];
    if (!next) return;
    setTransitioning(true);
    try {
      await updateOrderStatus(id, next);
      await reload();
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
    } finally {
      setTransitioning(false);
    }
  }

  async function handleSaveDetails() {
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
  }

  async function handleItemStatusChange(
    itemId: string,
    field: "production_status" | "installation_status",
    value: string
  ) {
    await updateOrderItem(id, itemId, { [field]: value || null });
    await reload();
  }

  if (loading || !order) return <TableSkeleton rows={5} columns={5} />;

  const isTerminal = order.status === "completed" || order.status === "cancelled";
  const nextStatus = NEXT_STATUS[order.status];

  return (
    <div className="flex flex-col gap-4">
      <Link href="/orders" className="text-sm text-primary hover:underline">
        ← {t("backToOrders")}
      </Link>

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
          )}

          {items.length > 0 && (
            <div className="p-3">
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
                          disabled={isTerminal}
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
                          disabled={isTerminal}
                        >
                          <option value="">—</option>
                          {INST_STATUSES.map((s) => (
                            <option key={s} value={s}>{t(`instStatus_${s}` as any)}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-2 py-1 text-xs text-text-secondary">{item.item_type}</td>
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
          )}
        </Card>
      ))}
    </div>
  );
}
