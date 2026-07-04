import { apiRequest } from "../api-client";
import type { Paginated, WorkOrder, WorkOrderItem } from "../types";

const BASE = "/api/v1/production";

export function listWorkOrders(
  params: { status?: string; search?: string; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<WorkOrder>>(BASE, {
    searchParams: {
      status: params.status,
      search: params.search || undefined,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createWorkOrder(orderId: string) {
  return apiRequest<WorkOrder>(BASE, { method: "POST", body: { order_id: orderId } });
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

export function listWorkOrderItems(id: string) {
  return apiRequest<{ items: WorkOrderItem[] }>(`${BASE}/${id}/items`);
}
