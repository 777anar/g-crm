"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
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
import { TableSkeleton } from "@/components/ui/skeleton";

type SectionData = {
  section: OrderSection;
  items: OrderItem[];
  measurements: OrderMeasurement[];
};

const STATUS_COLORS: Record<string, string> = {
  waiting: "bg-gray-100 text-gray-700",
  measuring: "bg-yellow-100 text-yellow-700",
  approved_for_production: "bg-blue-100 text-blue-700",
  in_production: "bg-indigo-100 text-indigo-700",
  ready: "bg-purple-100 text-purple-700",
  delivered: "bg-teal-100 text-teal-700",
  installed: "bg-green-100 text-green-700",
  completed: "bg-green-200 text-green-800",
  cancelled: "bg-red-100 text-red-700",
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

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("orders");
  const tCommon = useTranslations("common");
  const router = useRouter();

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

  if (loading || !order) return <div className="page-container"><TableSkeleton /></div>;

  const isTerminal = order.status === "completed" || order.status === "cancelled";
  const nextStatus = NEXT_STATUS[order.status];

  return (
    <div className="page-container">
      <div className="mb-4">
        <Link href="/orders" className="back-link">← {t("backToOrders")}</Link>
      </div>

      {/* Header */}
      <div className="page-header mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title font-mono">{order.order_number}</h1>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[order.status] ?? ""}`}>
              {t(order.status as any)}
            </span>
          </div>
          <p className="page-subtitle text-xs text-muted-foreground mt-1">
            {t("fromQuote")}: {order.quote_id}
          </p>
        </div>
        {!isTerminal && (
          <div className="flex gap-2">
            {nextStatus && (
              <Button onClick={handleAdvance} disabled={transitioning}>
                {transitioning ? t("saving") : `→ ${t(nextStatus as any)}`}
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => setCancelMode(!cancelMode)}
            >
              {t("markCancelled")}
            </Button>
          </div>
        )}
      </div>

      {/* Cancel panel */}
      {cancelMode && (
        <div className="card mb-4 p-4 border-red-200 bg-red-50">
          <p className="text-sm font-medium text-red-700 mb-2">{t("cancelReason")}</p>
          <textarea
            className="input w-full mb-2"
            rows={2}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            placeholder="Optional reason…"
          />
          <div className="flex gap-2">
            <Button onClick={handleCancel} disabled={transitioning}>
              {t("cancelOrder")}
            </Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>
              {tCommon("cancel")}
            </Button>
          </div>
        </div>
      )}

      {/* Totals bar */}
      <div className="card mb-6 p-4 bg-slate-50 flex flex-wrap gap-6 text-sm">
        <div><span className="text-muted-foreground">{t("subtotal")}:</span> <strong>{order.currency} {parseFloat(order.subtotal_gross).toFixed(2)}</strong></div>
        {parseFloat(order.discount_amount) > 0 && (
          <div><span className="text-muted-foreground">{t("discount")}:</span> <strong>- {order.currency} {parseFloat(order.discount_amount).toFixed(2)}</strong></div>
        )}
        <div><span className="text-muted-foreground">{t("vat")} {order.vat_rate}%:</span> <strong>{order.currency} {parseFloat(order.vat_amount).toFixed(2)}</strong></div>
        <div className="ml-auto text-base"><span className="text-muted-foreground">{t("totalFinal")}:</span> <strong className="text-lg">{order.currency} {parseFloat(order.total_final).toFixed(2)}</strong></div>
      </div>

      {/* Details card */}
      <div className="card mb-6 p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-sm">{t("notes")}</h2>
          {!isTerminal && (
            <button
              className="text-xs text-blue-600 hover:underline"
              onClick={() => (editMode ? handleSaveDetails() : setEditMode(true))}
            >
              {editMode ? tCommon("save") : tCommon("edit")}
            </button>
          )}
        </div>
        {editMode ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
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
                <label className="text-xs text-muted-foreground">{label}</label>
                <input
                  className="input mt-0.5"
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
                <dt className="text-xs text-muted-foreground">{label}</dt>
                <dd>{val ?? tCommon("dash")}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      {/* Sections */}
      {sectionData?.map(({ section, items, measurements }) => (
        <div key={section.id} className="card mb-4">
          <div className="flex items-center justify-between p-4 border-b bg-slate-800 text-white rounded-t-lg">
            <h2 className="font-semibold">{section.name}</h2>
            <span className="text-sm">{order.currency} {parseFloat(section.subtotal_sale).toFixed(2)}</span>
          </div>

          {/* Measurements */}
          {measurements.length > 0 && (
            <div className="p-3 bg-slate-50 border-b text-sm">
              <p className="text-xs font-medium text-muted-foreground mb-2">{t("measurements")}</p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Label</th><th>L (mm)</th><th>W (mm)</th><th>Qty</th><th>Area m²</th><th>Required m²</th>
                  </tr>
                </thead>
                <tbody>
                  {measurements.map((m) => (
                    <tr key={m.id}>
                      <td>{m.label ?? "—"}</td>
                      <td>{m.length_mm ?? "—"}</td>
                      <td>{m.width_mm ?? "—"}</td>
                      <td>{m.quantity}</td>
                      <td>{m.area_m2 ? parseFloat(m.area_m2).toFixed(3) : "—"}</td>
                      <td>{m.required_area_m2 ? parseFloat(m.required_area_m2).toFixed(3) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Items */}
          {items.length > 0 && (
            <div className="p-3">
              <table className="data-table text-sm">
                <thead>
                  <tr>
                    <th>{t("productionStatus")}</th>
                    <th>{t("installationStatus")}</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Price</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <select
                          className="input input-sm"
                          value={item.production_status ?? ""}
                          onChange={(e) =>
                            handleItemStatusChange(item.id, "production_status", e.target.value)
                          }
                          disabled={isTerminal}
                        >
                          <option value="">—</option>
                          {PROD_STATUSES.map((s) => (
                            <option key={s} value={s}>{t(`prodStatus_${s}` as any)}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <select
                          className="input input-sm"
                          value={item.installation_status ?? ""}
                          onChange={(e) =>
                            handleItemStatusChange(item.id, "installation_status", e.target.value)
                          }
                          disabled={isTerminal}
                        >
                          <option value="">—</option>
                          {INST_STATUSES.map((s) => (
                            <option key={s} value={s}>{t(`instStatus_${s}` as any)}</option>
                          ))}
                        </select>
                      </td>
                      <td className="text-xs">{item.item_type}</td>
                      <td>{item.description || "—"}</td>
                      <td>{item.quantity}</td>
                      <td>{item.unit}</td>
                      <td>{parseFloat(item.unit_sale_price).toFixed(2)}</td>
                      <td className="font-medium">{parseFloat(item.line_total_sale).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
