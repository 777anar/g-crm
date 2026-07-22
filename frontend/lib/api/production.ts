import { apiRequest } from "../api-client";
import type { Paginated, ProductionJob, ProductionStage, WorkOrder, WorkOrderEvent, WorkOrderItem } from "../types";

const BASE = "/api/v1/production";

export function listWorkOrders(
  params: { status?: string; search?: string; sort?: string; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<WorkOrder>>(BASE, {
    searchParams: {
      status: params.status,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createWorkOrder(orderId: string, options: { priority?: string; due_date?: string } = {}) {
  return apiRequest<WorkOrder>(BASE, {
    method: "POST",
    body: { order_id: orderId, priority: options.priority, due_date: options.due_date },
  });
}

export function getWorkOrder(id: string) {
  return apiRequest<WorkOrder>(`${BASE}/${id}`);
}

export function getWorkOrderForOrder(orderId: string) {
  return apiRequest<WorkOrder>(`${BASE}/by-order/${orderId}`);
}

export function updateWorkOrderStatus(id: string, status: string, cancelledReason?: string) {
  return apiRequest<WorkOrder>(`${BASE}/${id}/status`, {
    method: "POST",
    body: { status, cancelled_reason: cancelledReason },
  });
}

export function updateWorkOrder(id: string, input: { due_date?: string; notes?: string }) {
  return apiRequest<WorkOrder>(`${BASE}/${id}`, { method: "PATCH", body: input });
}

export function listWorkOrderItems(id: string) {
  return apiRequest<{ items: WorkOrderItem[] }>(`${BASE}/${id}/items`);
}

// --- Production Job: priority / operator / stage / timeline (Phase 1) ----

export function getProductionJob(id: string) {
  return apiRequest<ProductionJob>(`${BASE}/${id}/job`);
}

export function getWorkOrderTimeline(id: string) {
  return apiRequest<{ items: WorkOrderEvent[] }>(`${BASE}/${id}/timeline`);
}

export function updateWorkOrderPriority(id: string, priority: string) {
  return apiRequest<WorkOrder>(`${BASE}/${id}/priority`, { method: "POST", body: { priority } });
}

export function assignWorkOrderOperator(id: string, operatorUserId: string | null) {
  return apiRequest<WorkOrder>(`${BASE}/${id}/assign`, {
    method: "POST",
    body: { operator_user_id: operatorUserId },
  });
}

export function updateWorkOrderStage(id: string, stageId: string | null) {
  return apiRequest<WorkOrder>(`${BASE}/${id}/stage`, { method: "POST", body: { stage_id: stageId } });
}

// --- Configurable production stages ---------------------------------------

export function listProductionStages() {
  return apiRequest<{ items: ProductionStage[] }>(`${BASE}/stages`);
}

export function createProductionStage(name: string, sortOrder?: number) {
  return apiRequest<ProductionStage>(`${BASE}/stages`, {
    method: "POST",
    body: { name, sort_order: sortOrder },
  });
}

export function updateProductionStage(
  id: string,
  input: { name?: string; sort_order?: number; is_active?: boolean }
) {
  return apiRequest<ProductionStage>(`${BASE}/stages/${id}`, { method: "PATCH", body: input });
}
