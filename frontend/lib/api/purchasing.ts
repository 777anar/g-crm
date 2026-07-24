import { apiRequest } from "../api-client";
import type { GoodsReceipt, Paginated, ProcurementDashboard, PurchaseAttachment, PurchaseOrder, PurchaseOrderLine, PurchaseReturn, PurchaseRFQ, Supplier, SupplierContact, SupplierMetrics } from "../types";

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
  tax_id?: string;
  payment_terms_days?: number;
  default_currency?: string;
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
    tax_id: string;
    payment_terms_days: number;
    default_currency: string;
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

export const purchasingTabs = [
  { labelKey: "tabDashboard", href: "/purchasing" }, { labelKey: "tabSuppliers", href: "/purchasing/suppliers" },
  { labelKey: "tabRfqs", href: "/purchasing/rfqs" }, { labelKey: "tabPurchaseOrders", href: "/purchasing/orders" },
  { labelKey: "tabReturns", href: "/purchasing/returns" },
] as const;

export function getProcurementDashboard() { return apiRequest<ProcurementDashboard>(`${BASE}/dashboard`); }
export function listSupplierContacts(id:string) { return apiRequest<SupplierContact[]>(`${BASE}/suppliers/${id}/contacts`); }
export function addSupplierContact(id:string,input:{name:string;job_title?:string;email?:string;phone?:string;is_primary?:boolean}) { return apiRequest<SupplierContact>(`${BASE}/suppliers/${id}/contacts`,{method:"POST",body:input}); }
export function deleteSupplierContact(id:string,contactId:string) { return apiRequest<void>(`${BASE}/suppliers/${id}/contacts/${contactId}`,{method:"DELETE"}); }
export function getSupplierMetrics(id:string) { return apiRequest<SupplierMetrics>(`${BASE}/suppliers/${id}/metrics`); }
export function listRFQs(params:{status?:string;search?:string}={}) { return apiRequest<PurchaseRFQ[]>(`${BASE}/rfqs`,{searchParams:params}); }
export function createRFQ(input:{supplier_id:string;currency?:string;response_due_date?:string;supplier_reference?:string;notes?:string;lines:Array<{material_id?:string;description:string;quantity:string;unit?:string;quoted_unit_cost?:string}>}) { return apiRequest<PurchaseRFQ>(`${BASE}/rfqs`,{method:"POST",body:input}); }
export function updateRFQStatus(id:string,status:string,quotedTotal?:string,supplierReference?:string) { return apiRequest<PurchaseRFQ>(`${BASE}/rfqs/${id}/status`,{method:"POST",body:{status,quoted_total:quotedTotal,supplier_reference:supplierReference}}); }
export function convertRFQ(id:string) { return apiRequest<PurchaseOrder>(`${BASE}/rfqs/${id}/convert`,{method:"POST"}); }
export function listPurchaseReturns() { return apiRequest<PurchaseReturn[]>(`${BASE}/returns`); }
export function createPurchaseReturn(input:{purchase_order_id:string;reason:string;lines:Array<{goods_receipt_id:string;quantity:string}>}) { return apiRequest<PurchaseReturn>(`${BASE}/returns`,{method:"POST",body:input}); }
export function completePurchaseReturn(id:string) { return apiRequest<PurchaseReturn>(`${BASE}/returns/${id}/complete`,{method:"POST"}); }
export function updatePurchasePayment(id:string,amountPaid:string,paymentDueDate?:string) { return apiRequest<PurchaseOrder>(`${BASE}/purchase-orders/${id}/payment`,{method:"POST",body:{amount_paid:amountPaid,payment_due_date:paymentDueDate}}); }
export function purchasingExportUrl(resource:"suppliers"|"purchase-orders") { return `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}${BASE}/export/${resource}`; }
export async function uploadPurchaseDocument(entityType:string,entityId:string,file:File,label?:string){const formData=new FormData();formData.append("module","purchasing");formData.append("related_entity_type",entityType);formData.append("related_entity_id",entityId);formData.append("file",file);const doc=await apiRequest<{id:string}>("/api/v1/core/documents",{method:"POST",formData});return apiRequest<PurchaseAttachment>(`${BASE}/attachments`,{method:"POST",body:{entity_type:entityType,entity_id:entityId,document_id:doc.id,label:label||file.name}});}
export function listPurchaseAttachments(entityType:string,entityId:string){return apiRequest<PurchaseAttachment[]>(`${BASE}/attachments`,{searchParams:{entity_type:entityType,entity_id:entityId}});}
