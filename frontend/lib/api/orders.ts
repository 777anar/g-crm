import { apiRequest } from "../api-client";
import type {
  Order,
  OrderItem,
  OrderMeasurement,
  OrderSection,
  Paginated,
} from "../types";

const BASE = "/api/v1/orders";

export function listOrders(
  params: {
    projectId?: string;
    customerId?: string;
    status?: string;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Order>>(BASE, {
    searchParams: {
      project_id: params.projectId,
      customer_id: params.customerId,
      status: params.status,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getOrder(id: string) {
  return apiRequest<Order>(`${BASE}/${id}`);
}

export function createOrder(quoteId: string) {
  return apiRequest<Order>(BASE, { method: "POST", body: { quote_id: quoteId } });
}

export function updateOrder(
  id: string,
  input: {
    notes?: string | null;
    production_notes?: string | null;
    installation_notes?: string | null;
    delivery_address?: string | null;
    scheduled_production_date?: string | null;
    scheduled_installation_date?: string | null;
  }
) {
  return apiRequest<Order>(`${BASE}/${id}`, { method: "PATCH", body: input });
}

export function updateOrderStatus(id: string, status: string, cancelledReason?: string) {
  return apiRequest<Order>(`${BASE}/${id}/status`, {
    method: "POST",
    body: { status, cancelled_reason: cancelledReason },
  });
}

export function listOrderSections(orderId: string) {
  return apiRequest<{ items: OrderSection[] }>(`${BASE}/${orderId}/sections`);
}

export function listSectionItems(orderId: string, sectionId: string) {
  return apiRequest<{ items: OrderItem[] }>(
    `${BASE}/${orderId}/sections/${sectionId}/items`
  );
}

export function listSectionMeasurements(orderId: string, sectionId: string) {
  return apiRequest<{ items: OrderMeasurement[] }>(
    `${BASE}/${orderId}/sections/${sectionId}/measurements`
  );
}

export function updateOrderItem(
  orderId: string,
  itemId: string,
  input: {
    production_status?: string | null;
    installation_status?: string | null;
    notes?: string | null;
  }
) {
  return apiRequest<OrderItem>(`${BASE}/${orderId}/items/${itemId}`, {
    method: "PATCH",
    body: input,
  });
}
