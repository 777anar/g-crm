import { apiRequest } from "../api-client";
import type { GoodsReceipt, Paginated, PurchaseOrder, PurchaseOrderLine, Supplier } from "../types";

const BASE = "/api/v1/purchasing";

// --- Suppliers ---------------------------------------------------------

export function listSuppliers(
  params: { includeHidden?: boolean; search?: string; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<Supplier>>(`${BASE}/suppliers`, {
    searchParams: {
      include_hidden: params.includeHidden,
      search: params.search || undefined,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getSupplier(id: string) {
  return apiRequest<Supplier>(`${BASE}/suppliers/${id}`);
}

export function createSupplier(input: {
  name: string;
  contact_name?: string;
  phone?: string;
  email?: string;
  address?: string;
  notes?: string;
}) {
  return apiRequest<Supplier>(`${BASE}/suppliers`, { method: "POST", body: input });
}

export function updateSupplier(
  id: string,
  input: Partial<{
    name: string;
    contact_name: string;
    phone: string;
    email: string;
    address: string;
    notes: string;
    status: string;
  }>
) {
  return apiRequest<Supplier>(`${BASE}/suppliers/${id}`, { method: "PATCH", body: input });
}

// --- Purchase Orders -----------------------------------------------------

export type PurchaseOrderLineDraft = {
  material_id?: string;
  description: string;
  quantity: string;
  unit?: string;
  unit_cost?: string;
};

export function listPurchaseOrders(
  params: {
    supplierId?: string;
    status?: string;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<PurchaseOrder>>(`${BASE}/purchase-orders`, {
    searchParams: {
      supplier_id: params.supplierId,
      status: params.status,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createPurchaseOrder(input: {
  supplier_id: string;
  lines: PurchaseOrderLineDraft[];
  currency?: string;
  notes?: string;
  expected_delivery_date?: string;
}) {
  return apiRequest<PurchaseOrder>(`${BASE}/purchase-orders`, { method: "POST", body: input });
}

export function getPurchaseOrder(id: string) {
  return apiRequest<PurchaseOrder>(`${BASE}/purchase-orders/${id}`);
}

export function updatePurchaseOrder(id: string, input: { notes?: string; expected_delivery_date?: string }) {
  return apiRequest<PurchaseOrder>(`${BASE}/purchase-orders/${id}`, { method: "PATCH", body: input });
}

export function updatePurchaseOrderStatus(id: string, status: string, cancelledReason?: string) {
  return apiRequest<PurchaseOrder>(`${BASE}/purchase-orders/${id}/status`, {
    method: "POST",
    body: { status, cancelled_reason: cancelledReason },
  });
}

export function listPurchaseOrderLines(purchaseOrderId: string) {
  return apiRequest<{ items: PurchaseOrderLine[] }>(`${BASE}/purchase-orders/${purchaseOrderId}/lines`);
}

export function receivePurchaseOrderLine(
  purchaseOrderId: string,
  lineId: string,
  input: {
    quantity_received: string;
    notes?: string;
    warehouse_id?: string;
    slab_number?: string;
    length_mm?: string;
    width_mm?: string;
  }
) {
  return apiRequest<GoodsReceipt>(`${BASE}/purchase-orders/${purchaseOrderId}/lines/${lineId}/receive`, {
    method: "POST",
    body: input,
  });
}

export function listGoodsReceipts(purchaseOrderId: string) {
  return apiRequest<{ items: GoodsReceipt[] }>(`${BASE}/purchase-orders/${purchaseOrderId}/receipts`);
}
