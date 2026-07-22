"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  getPurchaseOrder,
  getSupplier,
  listGoodsReceipts,
  listPurchaseOrderLines,
  receivePurchaseOrderLine,
  updatePurchaseOrder,
  updatePurchaseOrderStatus,
} from "@/lib/api/purchasing";
import { listWarehouses } from "@/lib/api/catalog";
import type { GoodsReceipt, PurchaseOrder, PurchaseOrderLine, Warehouse } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { PurchaseOrderStatusBadge } from "@/components/ui/badge";
import { TextField, SelectField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate, formatDateTime } from "@/lib/format";

const MANUAL_NEXT_STATUS: Record<string, string | null> = {
  draft: "sent",
  sent: "confirmed",
  confirmed: null,
  partially_received: null,
  received: null,
  cancelled: null,
};

const RECEIVABLE_STATUSES = new Set(["confirmed", "partially_received"]);

export default function PurchaseOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("purchasing");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const toast = useToast();

  const [order, setOrder] = useState<PurchaseOrder | null>(null);
  const [supplierName, setSupplierName] = useState<string | null>(null);
  const [lines, setLines] = useState<PurchaseOrderLine[] | null>(null);
  const [receipts, setReceipts] = useState<GoodsReceipt[] | null>(null);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const [notes, setNotes] = useState("");
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [savingDetails, setSavingDetails] = useState(false);

  const [receivingLineId, setReceivingLineId] = useState<string | null>(null);
  const [receiveQty, setReceiveQty] = useState("");
  const [receiveWarehouseId, setReceiveWarehouseId] = useState("");
  const [receiveSlabNumber, setReceiveSlabNumber] = useState("");
  const [receiveLength, setReceiveLength] = useState("");
  const [receiveWidth, setReceiveWidth] = useState("");
  const [receiving, setReceiving] = useState(false);

  const reload = useCallback(async () => {
    const [o, linesRes, receiptsRes] = await Promise.all([
      getPurchaseOrder(id),
      listPurchaseOrderLines(id),
      listGoodsReceipts(id),
    ]);
    setOrder(o);
    setNotes(o.notes ?? "");
    setExpectedDeliveryDate(o.expected_delivery_date ?? "");
    getSupplier(o.supplier_id).then((s) => setSupplierName(s.name)).catch(() => {});
    setLines(linesRes.items);
    setReceipts(receiptsRes.items);
    setLoading(false);
  }, [id]);

  useEffect(() => {
    reload();
    listWarehouses().then((res) => setWarehouses(res.items)).catch(() => {});
  }, [reload]);

  async function handleAdvance() {
    if (!order) return;
    const next = MANUAL_NEXT_STATUS[order.status];
    if (!next) return;
    setTransitioning(true);
    try {
      await updatePurchaseOrderStatus(id, next);
      toast.success(t("statusUpdated"));
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
      await updatePurchaseOrderStatus(id, "cancelled", cancelReason || undefined);
      setCancelMode(false);
      toast.success(t("statusUpdated"));
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleSaveDetails() {
    setSavingDetails(true);
    try {
      await updatePurchaseOrder(id, { notes, expected_delivery_date: expectedDeliveryDate || undefined });
      toast.success(t("detailsSaved"));
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setSavingDetails(false);
    }
  }

  function startReceiving(line: PurchaseOrderLine) {
    setReceivingLineId(line.id);
    setReceiveQty("");
    setReceiveWarehouseId("");
    setReceiveSlabNumber("");
    setReceiveLength("");
    setReceiveWidth("");
  }

  async function handleReceive(line: PurchaseOrderLine) {
    if (!receiveQty) return;
    setReceiving(true);
    try {
      await receivePurchaseOrderLine(id, line.id, {
        quantity_received: receiveQty,
        warehouse_id: receiveWarehouseId || undefined,
        slab_number: receiveSlabNumber || undefined,
        length_mm: receiveLength || undefined,
        width_mm: receiveWidth || undefined,
      });
      toast.success(t("receiptRecorded"));
      setReceivingLineId(null);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setReceiving(false);
    }
  }

  if (loading || !order) return <TableSkeleton rows={5} columns={4} />;

  const isTerminal = order.status === "received" || order.status === "cancelled";
  const nextStatus = MANUAL_NEXT_STATUS[order.status];
  const isDraft = order.status === "draft";
  const isReceivable = RECEIVABLE_STATUSES.has(order.status);

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("purchaseOrders"), href: "/purchasing/orders" }, { label: order.po_number }]} />

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-text-primary">{order.po_number}</h1>
            <PurchaseOrderStatusBadge status={order.status} />
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            {t("supplier")}: {supplierName ?? tCommon("loading")}
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
                {t("cancelOrder")}
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
            <Button onClick={handleCancel} disabled={transitioning}>{t("cancelOrder")}</Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      {order.cancelled_reason && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="text-sm text-danger">{t("cancelReason")}: {order.cancelled_reason}</p>
        </Card>
      )}

      <Card>
        <CardHeader title={t("orderDetails")} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <TextField
            label={t("expectedDeliveryDate")}
            type="date"
            value={expectedDeliveryDate}
            onChange={(e) => setExpectedDeliveryDate(e.target.value)}
            disabled={!isDraft}
          />
          <div className="sm:col-span-2">
            <TextField label={t("notes")} value={notes} onChange={(e) => setNotes(e.target.value)} disabled={!isDraft} />
          </div>
        </div>
        {isDraft && (
          <div className="mt-3 flex justify-end">
            <Button variant="secondary" loading={savingDetails} onClick={handleSaveDetails}>
              {tCommon("save")}
            </Button>
          </div>
        )}
      </Card>

      <Card className="p-0 overflow-hidden">
        <div className="border-b border-border bg-bg px-4 py-2 text-sm font-medium text-text-secondary">
          {t("lineItems")}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("description")}</th>
                <th className="px-4 py-2 font-medium">{t("quantity")}</th>
                <th className="px-4 py-2 font-medium">{t("unitCost")}</th>
                <th className="px-4 py-2 font-medium">{t("tableTotal")}</th>
                <th className="px-4 py-2 font-medium">{t("quantityReceived")}</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {lines?.map((line) => {
                const remaining = parseFloat(line.quantity) - parseFloat(line.quantity_received);
                const canReceive = isReceivable && remaining > 0;
                return (
                  <Fragment key={line.id}>
                    <tr className="border-t border-border">
                      <td className="px-4 py-2 text-text-primary">{line.description}</td>
                      <td className="px-4 py-2 text-text-secondary">
                        {line.quantity} {line.unit}
                      </td>
                      <td className="px-4 py-2 text-text-secondary">{order.currency} {parseFloat(line.unit_cost).toFixed(2)}</td>
                      <td className="px-4 py-2 text-text-primary">{order.currency} {parseFloat(line.line_total).toFixed(2)}</td>
                      <td className="px-4 py-2 text-text-secondary">
                        {line.quantity_received} / {line.quantity} {line.unit}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {canReceive && receivingLineId !== line.id && (
                          <Button variant="secondary" onClick={() => startReceiving(line)}>
                            {t("receive")}
                          </Button>
                        )}
                      </td>
                    </tr>
                    {receivingLineId === line.id && (
                      <tr className="border-t border-border bg-bg">
                        <td colSpan={6} className="px-4 py-3">
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
                            <TextField
                              label={t("quantityReceivedNow")}
                              type="number"
                              min="0"
                              step="0.001"
                              value={receiveQty}
                              onChange={(e) => setReceiveQty(e.target.value)}
                              hint={`${t("remaining")}: ${remaining}`}
                              required
                            />
                            <SelectField
                              label={t("receiveIntoWarehouse")}
                              value={receiveWarehouseId}
                              onChange={(e) => setReceiveWarehouseId(e.target.value)}
                              hint={t("receiveWarehouseHint")}
                            >
                              <option value="">{tCommon("dash")}</option>
                              {warehouses.map((w) => (
                                <option key={w.id} value={w.id}>
                                  {w.name}
                                </option>
                              ))}
                            </SelectField>
                            <TextField
                              label={t("slabNumber")}
                              value={receiveSlabNumber}
                              onChange={(e) => setReceiveSlabNumber(e.target.value)}
                            />
                            <TextField
                              label={t("lengthMm")}
                              type="number"
                              value={receiveLength}
                              onChange={(e) => setReceiveLength(e.target.value)}
                            />
                            <TextField
                              label={t("widthMm")}
                              type="number"
                              value={receiveWidth}
                              onChange={(e) => setReceiveWidth(e.target.value)}
                            />
                          </div>
                          <div className="mt-3 flex gap-2">
                            <Button loading={receiving} disabled={!receiveQty} onClick={() => handleReceive(line)}>
                              {t("confirmReceive")}
                            </Button>
                            <Button variant="secondary" onClick={() => setReceivingLineId(null)}>
                              {tCommon("cancel")}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {receipts && receipts.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <div className="border-b border-border bg-bg px-4 py-2 text-sm font-medium text-text-secondary">
            {t("receiptHistory")}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-text-secondary">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("quantityReceived")}</th>
                  <th className="px-4 py-2 font-medium">{t("receivedAt")}</th>
                  <th className="px-4 py-2 font-medium">{t("slabCreated")}</th>
                </tr>
              </thead>
              <tbody>
                {receipts.map((r) => (
                  <tr key={r.id} className="border-t border-border">
                    <td className="px-4 py-2 text-text-primary">{r.quantity_received}</td>
                    <td className="px-4 py-2 text-text-secondary">{formatDateTime(r.received_at)}</td>
                    <td className="px-4 py-2 text-text-secondary">{r.slab_id ? tCommon("yes") : tCommon("dash")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <p className="text-xs text-text-secondary">
        {t("created")}: {formatDate(order.created_at)}
      </p>
    </div>
  );
}
