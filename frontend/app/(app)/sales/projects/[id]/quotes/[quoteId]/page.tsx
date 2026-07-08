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
  updateQuote,
  downloadQuotePdf,
} from "@/lib/api/sales";
import type { Quote, QuoteSection, QuoteSectionItem, QuoteSectionMeasurement } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { QuoteStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { ApiRequestError } from "@/lib/api-client";

type SectionData = {
  section: QuoteSection;
  items: QuoteSectionItem[];
  measurements: QuoteSectionMeasurement[];
};

const ITEM_TYPES = [
  "material", "wall_cladding", "vanity", "backsplash",
  "edge_profile", "sink_cutout", "cooktop_cutout", "faucet_hole",
  "installation", "transport", "crane", "other",
];

const inputClasses =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary";

export default function QuoteBuilderPage() {
  const { id, quoteId } = useParams<{ id: string; quoteId: string }>();
  const t = useTranslations("sales");
  const tOrders = useTranslations("orders");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const confirm = useConfirm();

  const [quote, setQuote] = useState<Quote | null>(null);
  const [sectionData, setSectionData] = useState<SectionData[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [newSectionName, setNewSectionName] = useState("");
  const [addingSection, setAddingSection] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    try {
      const order = await createOrder(quoteId);
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }

  async function handleDownloadPdf() {
    if (!quote) return;
    setDownloading(true);
    try {
      await downloadQuotePdf(quoteId, quote.quote_number);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    } finally {
      setDownloading(false);
    }
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
    if (!(await confirm(tCommon("confirmDelete")))) return;
    try {
      await deleteSection(sectionId);
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
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

  async function handleUpdateQuoteField(field: Parameters<typeof updateQuote>[1]) {
    try {
      const newQuote = await updateQuote(quoteId, field);
      setQuote(newQuote);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }

  if (loading || !quote) return <TableSkeleton rows={5} columns={5} />;

  return (
    <div className="flex flex-col gap-4">
      <Link href={`/sales/projects/${id}`} className="text-sm text-primary hover:underline">
        ← {t("backToProject")}
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-text-primary">{quote.quote_number}</h1>
            <QuoteStatusBadge status={quote.status} />
          </div>
          <p className="text-sm text-text-secondary">v{quote.version}</p>
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
            <Button onClick={handleCreateOrder}>{tOrders("createOrder")}</Button>
          )}
          <Button variant="secondary" onClick={handleDownloadPdf} disabled={downloading}>
            {downloading ? t("saving") : t("downloadPdf")}
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {/* Totals bar */}
      <Card className="flex flex-wrap gap-6 text-sm">
        <div><span className="text-text-secondary">{t("subtotal")}:</span> <strong className="text-text-primary">{quote.currency} {parseFloat(quote.subtotal_gross).toFixed(2)}</strong></div>
        {parseFloat(quote.discount_value) > 0 && (
          <div><span className="text-text-secondary">{t("discount")}:</span> <strong className="text-text-primary">− {quote.currency} {parseFloat(quote.discount_amount).toFixed(2)}</strong></div>
        )}
        <div><span className="text-text-secondary">{t("vat")} {quote.vat_rate}%:</span> <strong className="text-text-primary">{quote.currency} {parseFloat(quote.vat_amount).toFixed(2)}</strong></div>
        <div className="ml-auto text-base"><span className="text-text-secondary">{t("totalFinal")}:</span> <strong className="text-lg text-primary">{quote.currency} {parseFloat(quote.total_final).toFixed(2)}</strong></div>
      </Card>

      {/* Quote settings */}
      <Card className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-text-primary">{t("quoteSettings")}</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t("currency")}</span>
            {isEditable ? (
              <input
                className={inputClasses}
                defaultValue={quote.currency}
                maxLength={3}
                onBlur={(e) => e.target.value.trim() && handleUpdateQuoteField({ currency: e.target.value.trim().toUpperCase() })}
              />
            ) : (
              <span className="text-text-primary">{quote.currency}</span>
            )}
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t("vatRate")}</span>
            {isEditable ? (
              <input
                className={inputClasses}
                defaultValue={quote.vat_rate}
                onBlur={(e) => e.target.value !== "" && handleUpdateQuoteField({ vat_rate: e.target.value })}
              />
            ) : (
              <span className="text-text-primary">{quote.vat_rate}%</span>
            )}
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t("discount")}</span>
            {isEditable ? (
              <select
                className={inputClasses}
                defaultValue={quote.discount_type}
                onChange={(e) => handleUpdateQuoteField({ discount_type: e.target.value })}
              >
                <option value="none">{t("discountTypeNone")}</option>
                <option value="percent">{t("discountTypePercent")}</option>
                <option value="fixed">{t("discountTypeFixed")}</option>
              </select>
            ) : (
              <span className="text-text-primary">{t(`discountType${quote.discount_type === "percent" ? "Percent" : quote.discount_type === "fixed" ? "Fixed" : "None"}`)}</span>
            )}
          </label>
          {quote.discount_type !== "none" && (
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-text-secondary">{t("discountValue")}</span>
              {isEditable ? (
                <input
                  className={inputClasses}
                  defaultValue={quote.discount_value}
                  onBlur={(e) => e.target.value !== "" && handleUpdateQuoteField({ discount_value: e.target.value })}
                />
              ) : (
                <span className="text-text-primary">{quote.discount_value}{quote.discount_type === "percent" ? "%" : ` ${quote.currency}`}</span>
              )}
            </label>
          )}
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t("validUntil")}</span>
            {isEditable ? (
              <input
                type="date"
                className={inputClasses}
                defaultValue={quote.valid_until ? quote.valid_until.slice(0, 10) : ""}
                onBlur={(e) => handleUpdateQuoteField({ valid_until: e.target.value || null })}
              />
            ) : (
              <span className="text-text-primary">{quote.valid_until ? quote.valid_until.slice(0, 10) : "—"}</span>
            )}
          </label>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t("internalNotes")}</span>
            {isEditable ? (
              <textarea
                className={inputClasses}
                rows={2}
                defaultValue={quote.internal_notes ?? ""}
                onBlur={(e) => handleUpdateQuoteField({ internal_notes: e.target.value || null })}
              />
            ) : (
              <span className="text-text-primary">{quote.internal_notes || "—"}</span>
            )}
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t("customerNotes")}</span>
            {isEditable ? (
              <textarea
                className={inputClasses}
                rows={2}
                defaultValue={quote.customer_notes ?? ""}
                onBlur={(e) => handleUpdateQuoteField({ customer_notes: e.target.value || null })}
              />
            ) : (
              <span className="text-text-primary">{quote.customer_notes || "—"}</span>
            )}
          </label>
        </div>
      </Card>

      {/* Sections */}
      {sectionData?.map(({ section, items, measurements }) => (
        <Card key={section.id} className="p-0 overflow-hidden">
          <div className="flex items-center justify-between bg-text-primary px-4 py-3 text-white">
            <h2 className="font-semibold">{section.name}</h2>
            <div className="flex items-center gap-4 text-sm">
              <span>{t("subtotal")}: {parseFloat(section.subtotal_sale).toFixed(2)}</span>
              {isEditable && (
                <button onClick={() => handleDeleteSection(section.id)} className="text-white/60 hover:text-white">
                  ✕
                </button>
              )}
            </div>
          </div>

          {measurements.length > 0 && (
            <div className="border-b border-border bg-bg p-3">
              <div className="mb-2 text-xs font-medium text-text-secondary">{t("measurements")}</div>
              <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-text-secondary">
                  <tr>
                    <th className="px-2 py-1 font-medium">{t("label")}</th>
                    <th className="px-2 py-1 font-medium">{t("lengthMm")}</th>
                    <th className="px-2 py-1 font-medium">{t("widthMm")}</th>
                    <th className="px-2 py-1 font-medium">{t("quantity")}</th>
                    <th className="px-2 py-1 font-medium">{t("areaSqm")}</th>
                    <th className="px-2 py-1 font-medium">{t("wastePct")}</th>
                    <th className="px-2 py-1 font-medium">{t("requiredArea")}</th>
                    {isEditable && <th className="px-2 py-1" />}
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
                      <td className="px-2 py-1">{m.waste_pct}%</td>
                      <td className="px-2 py-1">{m.required_area_m2 ? parseFloat(m.required_area_m2).toFixed(3) : "—"}</td>
                      {isEditable && (
                        <td className="px-2 py-1">
                          <button onClick={() => handleDeleteMeasurement(m.id)} className="text-xs text-danger hover:underline">✕</button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          )}

          <div className="p-3">
            {items.length > 0 && (
              <div className="overflow-x-auto">
              <table className="mb-3 w-full text-left text-sm">
                <thead className="text-text-secondary">
                  <tr>
                    <th className="px-2 py-1 font-medium">{t("itemType")}</th>
                    <th className="px-2 py-1 font-medium">{t("description")}</th>
                    <th className="px-2 py-1 font-medium">{t("quantity")}</th>
                    <th className="px-2 py-1 font-medium">{t("unit")}</th>
                    <th className="px-2 py-1 font-medium">{t("unitPrice")}</th>
                    <th className="px-2 py-1 font-medium">{t("lineTotal")}</th>
                    {isEditable && <th className="px-2 py-1" />}
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-border">
                      <td className="px-2 py-1 text-xs text-text-secondary">{item.item_type}</td>
                      <td className="px-2 py-1">{item.description || "—"}</td>
                      <td className="px-2 py-1">
                        {isEditable ? (
                          <input
                            className={`${inputClasses} w-16`}
                            defaultValue={item.quantity}
                            onBlur={(e) => handleUpdateItemPrice(item.id, "quantity", e.target.value)}
                          />
                        ) : item.quantity}
                      </td>
                      <td className="px-2 py-1">{item.unit}</td>
                      <td className="px-2 py-1">
                        {isEditable ? (
                          <input
                            className={`${inputClasses} w-24`}
                            defaultValue={item.unit_sale_price}
                            onBlur={(e) => handleUpdateItemPrice(item.id, "unit_sale_price", e.target.value)}
                          />
                        ) : parseFloat(item.unit_sale_price).toFixed(2)}
                      </td>
                      <td className="px-2 py-1 font-medium text-text-primary">{parseFloat(item.line_total_sale).toFixed(2)}</td>
                      {isEditable && (
                        <td className="px-2 py-1">
                          <button onClick={() => handleDeleteItem(item.id)} className="text-xs text-danger hover:underline">✕</button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}

            {isEditable && (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="self-center text-xs text-text-secondary">{t("addItem")}:</span>
                {ITEM_TYPES.map((type) => (
                  <button
                    key={type}
                    onClick={() => handleAddItem(section.id, type)}
                    className="rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-bg"
                  >
                    + {type.replace("_", " ")}
                  </button>
                ))}
                <button
                  onClick={() => handleAddMeasurement(section.id)}
                  className="rounded-md border border-primary/40 px-2 py-1 text-xs text-primary hover:bg-primary/10"
                >
                  + {t("addMeasurement")}
                </button>
              </div>
            )}
          </div>
        </Card>
      ))}

      {/* Add section */}
      {isEditable && (
        <div className="flex gap-2">
          <input
            className={`${inputClasses} flex-1`}
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
