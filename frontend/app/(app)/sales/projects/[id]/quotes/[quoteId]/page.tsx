"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { createOrder } from "@/lib/api/orders";
import {
  getQuote,
  listSections,
  createSection,
  deleteSection,
  listItems,
  createItem,
  updateItem,
  deleteItem,
  listMeasurements,
  createMeasurement,
  deleteMeasurement,
  updateQuoteStatus,
  getQuotePdfUrl,
} from "@/lib/api/sales";
import type {
  Quote,
  QuoteSection,
  QuoteSectionItem,
  QuoteSectionMeasurement,
  QUOTE_ITEM_TYPES,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { TableSkeleton } from "@/components/ui/skeleton";

type SectionData = {
  section: QuoteSection;
  items: QuoteSectionItem[];
  measurements: QuoteSectionMeasurement[];
};

export default function QuoteBuilderPage() {
  const { id, quoteId } = useParams<{ id: string; quoteId: string }>();
  const t = useTranslations("sales");
  const tOrders = useTranslations("orders");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [quote, setQuote] = useState<Quote | null>(null);
  const [sectionData, setSectionData] = useState<SectionData[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [newSectionName, setNewSectionName] = useState("");
  const [addingSection, setAddingSection] = useState(false);

  const reload = useCallback(async () => {
    const [q, secs] = await Promise.all([getQuote(quoteId), listSections(quoteId)]);
    const enriched = await Promise.all(
      secs.items.map(async (s) => {
        const [itemsRes, meaRes] = await Promise.all([
          listItems(s.id),
          listMeasurements(s.id),
        ]);
        return { section: s, items: itemsRes.items, measurements: meaRes.items };
      })
    );
    setQuote(q);
    setSectionData(enriched);
    setLoading(false);
  }, [quoteId]);

  useEffect(() => { reload(); }, [reload]);

  const isEditable = quote?.status === "draft";

  async function handleCreateOrder() {
    const order = await createOrder(quoteId);
    router.push(`/orders/${order.id}`);
  }

  async function handleAddSection() {
    if (!newSectionName.trim()) return;
    setAddingSection(true);
    try {
      await createSection(quoteId, { name: newSectionName.trim(), sort_order: (sectionData?.length ?? 0) });
      setNewSectionName("");
      await reload();
    } finally {
      setAddingSection(false);
    }
  }

  async function handleDeleteSection(sectionId: string) {
    if (!confirm(tCommon("confirmDelete"))) return;
    await deleteSection(sectionId);
    await reload();
  }

  async function handleAddItem(sectionId: string, itemType: string) {
    await createItem(sectionId, { item_type: itemType, quantity: "1", unit_sale_price: "0" });
    await reload();
  }

  async function handleUpdateItemPrice(
    itemId: string,
    field: "unit_sale_price" | "unit_cost_price" | "quantity",
    value: string
  ) {
    await updateItem(itemId, { [field]: value });
    await reload();
  }

  async function handleDeleteItem(itemId: string) {
    await deleteItem(itemId);
    await reload();
  }

  async function handleAddMeasurement(sectionId: string) {
    await createMeasurement(sectionId, { quantity: 1, waste_pct: "10" });
    await reload();
  }

  async function handleDeleteMeasurement(measurementId: string) {
    await deleteMeasurement(measurementId);
    await reload();
  }

  async function handleStatusChange(status: string) {
    const newQuote = await updateQuoteStatus(quoteId, status);
    setQuote(newQuote);
    if (newQuote.id !== quoteId) {
      router.replace(`/sales/projects/${id}/quotes/${newQuote.id}`);
    }
  }

  function statusColor(status: string) {
    const map: Record<string, string> = {
      draft: "bg-gray-100 text-gray-700",
      sent: "bg-blue-100 text-blue-700",
      negotiation: "bg-yellow-100 text-yellow-700",
      accepted: "bg-green-100 text-green-700",
      rejected: "bg-red-100 text-red-700",
      expired: "bg-orange-100 text-orange-700",
    };
    return map[status] ?? "bg-gray-100 text-gray-600";
  }

  const ITEM_TYPES = [
    "material", "wall_cladding", "vanity", "backsplash",
    "edge_profile", "sink_cutout", "cooktop_cutout", "faucet_hole",
    "installation", "transport", "crane", "other",
  ];

  if (loading || !quote) return <div className="page-container"><TableSkeleton /></div>;

  return (
    <div className="page-container">
      <div className="mb-4">
        <Link href={`/sales/projects/${id}`} className="back-link">← {t("backToProject")}</Link>
      </div>

      {/* Header */}
      <div className="page-header mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title font-mono">{quote.quote_number}</h1>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor(quote.status)}`}>
              {t(quote.status as any)}
            </span>
          </div>
          <p className="page-subtitle">v{quote.version}</p>
        </div>
        <div className="flex gap-2">
          {quote.status === "draft" && (
            <Button variant="secondary" onClick={() => handleStatusChange("sent")}>{t("markSent")}</Button>
          )}
          {(quote.status === "sent" || quote.status === "negotiation") && (
            <>
              <Button variant="secondary" onClick={() => handleStatusChange("accepted")}>{t("markAccepted")}</Button>
              <Button variant="secondary" onClick={() => handleStatusChange("rejected")}>{t("markRejected")}</Button>
            </>
          )}
          {quote.status === "accepted" && (
            <Button onClick={handleCreateOrder}>
              {tOrders("createOrder")}
            </Button>
          )}
          <a
            href={getQuotePdfUrl(quoteId)}
            target="_blank"
            rel="noreferrer"
            className="btn btn-secondary"
          >
            {t("downloadPdf")}
          </a>
        </div>
      </div>

      {/* Totals bar */}
      <div className="card mb-6 p-4 bg-slate-50 flex flex-wrap gap-6 text-sm">
        <div><span className="text-muted-foreground">{t("subtotal")}:</span> <strong>{quote.currency} {parseFloat(quote.subtotal_gross).toFixed(2)}</strong></div>
        {parseFloat(quote.discount_value) > 0 && (
          <div><span className="text-muted-foreground">{t("discount")}:</span> <strong>- {quote.currency} {parseFloat(quote.discount_amount).toFixed(2)}</strong></div>
        )}
        <div><span className="text-muted-foreground">{t("vat")} {quote.vat_rate}%:</span> <strong>{quote.currency} {parseFloat(quote.vat_amount).toFixed(2)}</strong></div>
        <div className="ml-auto text-base"><span className="text-muted-foreground">{t("totalFinal")}:</span> <strong className="text-lg">{quote.currency} {parseFloat(quote.total_final).toFixed(2)}</strong></div>
      </div>

      {/* Sections */}
      {sectionData?.map(({ section, items, measurements }) => (
        <div key={section.id} className="card mb-4">
          {/* Section header */}
          <div className="flex items-center justify-between p-4 border-b bg-slate-800 text-white rounded-t-lg">
            <h2 className="font-semibold">{section.name}</h2>
            <div className="flex items-center gap-4 text-sm">
              <span>{t("subtotal")}: {parseFloat(section.subtotal_sale).toFixed(2)}</span>
              {isEditable && (
                <button
                  onClick={() => handleDeleteSection(section.id)}
                  className="text-slate-400 hover:text-white text-xs"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {/* Measurements */}
          {measurements.length > 0 && (
            <div className="p-3 bg-slate-50 border-b">
              <div className="text-xs font-medium text-muted-foreground mb-2">{t("measurements")}</div>
              <table className="data-table text-sm">
                <thead>
                  <tr>
                    <th>{t("label")}</th>
                    <th>{t("lengthMm")}</th>
                    <th>{t("widthMm")}</th>
                    <th>{t("quantity")}</th>
                    <th>{t("areaSqm")}</th>
                    <th>{t("wastePct")}</th>
                    <th>{t("requiredArea")}</th>
                    {isEditable && <th></th>}
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
                      <td>{m.waste_pct}%</td>
                      <td>{m.required_area_m2 ? parseFloat(m.required_area_m2).toFixed(3) : "—"}</td>
                      {isEditable && (
                        <td>
                          <button
                            onClick={() => handleDeleteMeasurement(m.id)}
                            className="text-red-400 hover:text-red-600 text-xs"
                          >
                            ✕
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Items */}
          <div className="p-3">
            {items.length > 0 && (
              <table className="data-table text-sm mb-3">
                <thead>
                  <tr>
                    <th>{t("itemType")}</th>
                    <th>{t("description")}</th>
                    <th>{t("quantity")}</th>
                    <th>{t("unit")}</th>
                    <th>{t("unitPrice")}</th>
                    <th>{t("lineTotal")}</th>
                    {isEditable && <th></th>}
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td className="text-xs">{item.item_type}</td>
                      <td>{item.description || "—"}</td>
                      <td>
                        {isEditable ? (
                          <input
                            className="input input-sm w-16"
                            defaultValue={item.quantity}
                            onBlur={(e) => handleUpdateItemPrice(item.id, "quantity", e.target.value)}
                          />
                        ) : item.quantity}
                      </td>
                      <td>{item.unit}</td>
                      <td>
                        {isEditable ? (
                          <input
                            className="input input-sm w-24"
                            defaultValue={item.unit_sale_price}
                            onBlur={(e) => handleUpdateItemPrice(item.id, "unit_sale_price", e.target.value)}
                          />
                        ) : parseFloat(item.unit_sale_price).toFixed(2)}
                      </td>
                      <td className="font-medium">{parseFloat(item.line_total_sale).toFixed(2)}</td>
                      {isEditable && (
                        <td>
                          <button
                            onClick={() => handleDeleteItem(item.id)}
                            className="text-red-400 hover:text-red-600 text-xs"
                          >
                            ✕
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {isEditable && (
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="text-xs text-muted-foreground self-center">{t("addItem")}:</span>
                {ITEM_TYPES.map((type) => (
                  <button
                    key={type}
                    onClick={() => handleAddItem(section.id, type)}
                    className="px-2 py-1 text-xs rounded border hover:bg-slate-100"
                  >
                    + {type.replace("_", " ")}
                  </button>
                ))}
                <button
                  onClick={() => handleAddMeasurement(section.id)}
                  className="px-2 py-1 text-xs rounded border border-blue-300 text-blue-600 hover:bg-blue-50"
                >
                  + {t("addMeasurement")}
                </button>
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Add section */}
      {isEditable && (
        <div className="flex gap-2 mt-4">
          <input
            className="input flex-1"
            placeholder={t("sectionName")}
            value={newSectionName}
            onChange={(e) => setNewSectionName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddSection()}
          />
          <Button onClick={handleAddSection} disabled={addingSection || !newSectionName.trim()}>
            {addingSection ? t("creating") : t("addSection")}
          </Button>
        </div>
      )}
    </div>
  );
}
