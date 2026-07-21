import { apiRequest } from "../api-client";
import type { PortalAccess } from "../types";

const BASE = "/api/v1/customer_portal/admin";

export function getPortalAccess(customerId: string) {
  return apiRequest<PortalAccess>(`${BASE}/customers/${customerId}/access`);
}

export function enablePortalAccess(customerId: string, input: { email: string; password: string }) {
  return apiRequest<PortalAccess>(`${BASE}/customers/${customerId}/access`, { method: "POST", body: input });
}

export function resetPortalPassword(customerId: string, password: string) {
  return apiRequest<PortalAccess>(`${BASE}/customers/${customerId}/access/reset-password`, {
    method: "POST",
    body: { password },
  });
}

export function setPortalAccessActive(customerId: string, isActive: boolean) {
  return apiRequest<PortalAccess>(`${BASE}/customers/${customerId}/access/status`, {
    method: "POST",
    body: { is_active: isActive },
  });
}
