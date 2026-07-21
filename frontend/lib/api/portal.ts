import { portalApiRequest } from "../portal-api-client";
import type {
  Paginated,
  PortalDocument,
  PortalInstallationJob,
  PortalInvoice,
  PortalMe,
  PortalOrder,
  PortalQuote,
} from "../types";

const BASE = "/api/v1/customer_portal";

export function portalLogin(email: string, password: string) {
  return portalApiRequest<{ access_token: string; refresh_token: string }>(`${BASE}/auth/login`, {
    method: "POST",
    body: { email, password },
  });
}

export function portalLogout(refreshToken: string) {
  return portalApiRequest<{ status: string }>(`${BASE}/auth/logout`, {
    method: "POST",
    body: { refresh_token: refreshToken },
  });
}

export function getPortalMe() {
  return portalApiRequest<PortalMe>(`${BASE}/me`);
}

export function listPortalOrders(params: { limit?: number; cursor?: string } = {}) {
  return portalApiRequest<Paginated<PortalOrder>>(`${BASE}/me/orders`, { searchParams: params });
}

export function getPortalOrder(id: string) {
  return portalApiRequest<PortalOrder>(`${BASE}/me/orders/${id}`);
}

export function listPortalQuotes(params: { limit?: number; cursor?: string } = {}) {
  return portalApiRequest<Paginated<PortalQuote>>(`${BASE}/me/quotes`, { searchParams: params });
}

export function getPortalQuote(id: string) {
  return portalApiRequest<PortalQuote>(`${BASE}/me/quotes/${id}`);
}

export function listPortalInvoices(params: { limit?: number; cursor?: string } = {}) {
  return portalApiRequest<Paginated<PortalInvoice>>(`${BASE}/me/invoices`, { searchParams: params });
}

export function getPortalInvoice(id: string) {
  return portalApiRequest<PortalInvoice>(`${BASE}/me/invoices/${id}`);
}

export function listPortalInstallationJobs(params: { limit?: number; cursor?: string } = {}) {
  return portalApiRequest<Paginated<PortalInstallationJob>>(`${BASE}/me/installation-jobs`, { searchParams: params });
}

export function listPortalDocuments(params: { limit?: number; cursor?: string } = {}) {
  return portalApiRequest<Paginated<PortalDocument>>(`${BASE}/me/documents`, { searchParams: params });
}

export function getPortalDocumentDownloadUrl(id: string) {
  return portalApiRequest<{ url: string }>(`${BASE}/me/documents/${id}/download`);
}
