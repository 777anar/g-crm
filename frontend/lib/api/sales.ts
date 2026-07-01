import { apiRequest } from "../api-client";
import type {
  Paginated,
  Project,
  Quote,
  QuoteSection,
  QuoteSectionItem,
  QuoteSectionMeasurement,
  ServicePrice,
} from "../types";

const BASE = "/api/v1/sales";

// ── Projects ──────────────────────────────────────────────────────────────────

export function listProjects(
  params: {
    customerId?: string;
    status?: string;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Project>>(`${BASE}/projects`, {
    searchParams: {
      customer_id: params.customerId,
      status: params.status,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getProject(id: string) {
  return apiRequest<Project>(`${BASE}/projects/${id}`);
}

export function createProject(input: {
  customer_id: string;
  name: string;
  project_type?: string;
  address?: string;
  notes?: string;
  assigned_to?: string;
}) {
  return apiRequest<Project>(`${BASE}/projects`, { method: "POST", body: input });
}

export function updateProject(
  id: string,
  input: {
    name?: string;
    project_type?: string;
    address?: string;
    notes?: string;
    assigned_to?: string;
    status?: string;
  }
) {
  return apiRequest<Project>(`${BASE}/projects/${id}`, { method: "PATCH", body: input });
}

// ── Quotes ────────────────────────────────────────────────────────────────────

export function listQuotes(projectId: string, params: { limit?: number; cursor?: string } = {}) {
  return apiRequest<Paginated<Quote>>(`${BASE}/projects/${projectId}/quotes`, {
    searchParams: { limit: params.limit, cursor: params.cursor },
  });
}

export function getQuote(id: string) {
  return apiRequest<Quote>(`${BASE}/quotes/${id}`);
}

export function createQuote(
  projectId: string,
  input: {
    currency?: string;
    price_list_id?: string;
    valid_until?: string;
    internal_notes?: string;
    customer_notes?: string;
    vat_rate?: string;
    discount_type?: string;
    discount_value?: string;
  } = {}
) {
  return apiRequest<Quote>(`${BASE}/projects/${projectId}/quotes`, { method: "POST", body: input });
}

export function updateQuote(
  id: string,
  input: {
    currency?: string;
    price_list_id?: string | null;
    valid_until?: string | null;
    internal_notes?: string | null;
    customer_notes?: string | null;
    vat_rate?: string;
    discount_type?: string;
    discount_value?: string;
  }
) {
  return apiRequest<Quote>(`${BASE}/quotes/${id}`, { method: "PATCH", body: input });
}

export function updateQuoteStatus(id: string, status: string) {
  return apiRequest<Quote>(`${BASE}/quotes/${id}/status`, { method: "POST", body: { status } });
}

export function getQuotePdfUrl(id: string) {
  return `${BASE}/quotes/${id}/pdf`;
}

// ── Sections ──────────────────────────────────────────────────────────────────

export function listSections(quoteId: string) {
  return apiRequest<{ items: QuoteSection[] }>(`${BASE}/quotes/${quoteId}/sections`);
}

export function createSection(
  quoteId: string,
  input: { name: string; sort_order?: number; notes?: string }
) {
  return apiRequest<QuoteSection>(`${BASE}/quotes/${quoteId}/sections`, {
    method: "POST",
    body: input,
  });
}

export function updateSection(
  id: string,
  input: { name?: string; sort_order?: number; notes?: string }
) {
  return apiRequest<QuoteSection>(`${BASE}/sections/${id}`, { method: "PATCH", body: input });
}

export function deleteSection(id: string) {
  return apiRequest<void>(`${BASE}/sections/${id}`, { method: "DELETE" });
}

// ── Measurements ──────────────────────────────────────────────────────────────

export function listMeasurements(sectionId: string) {
  return apiRequest<{ items: QuoteSectionMeasurement[] }>(
    `${BASE}/sections/${sectionId}/measurements`
  );
}

export function createMeasurement(
  sectionId: string,
  input: {
    label?: string;
    length_mm?: string;
    width_mm?: string;
    thickness_mm?: string;
    quantity?: number;
    waste_pct?: string;
    override_required_area?: boolean;
    required_area_m2?: string;
    notes?: string;
    sort_order?: number;
  }
) {
  return apiRequest<QuoteSectionMeasurement>(
    `${BASE}/sections/${sectionId}/measurements`,
    { method: "POST", body: input }
  );
}

export function updateMeasurement(id: string, input: Record<string, unknown>) {
  return apiRequest<QuoteSectionMeasurement>(`${BASE}/measurements/${id}`, {
    method: "PATCH",
    body: input,
  });
}

export function deleteMeasurement(id: string) {
  return apiRequest<void>(`${BASE}/measurements/${id}`, { method: "DELETE" });
}

// ── Items ─────────────────────────────────────────────────────────────────────

export function listItems(sectionId: string) {
  return apiRequest<{ items: QuoteSectionItem[] }>(`${BASE}/sections/${sectionId}/items`);
}

export function createItem(
  sectionId: string,
  input: {
    item_type: string;
    description?: string;
    material_id?: string;
    slab_id?: string;
    quantity?: string;
    unit?: string;
    unit_sale_price?: string;
    unit_cost_price?: string;
    notes?: string;
    sort_order?: number;
  }
) {
  return apiRequest<QuoteSectionItem>(`${BASE}/sections/${sectionId}/items`, {
    method: "POST",
    body: input,
  });
}

export function updateItem(id: string, input: Record<string, unknown>) {
  return apiRequest<QuoteSectionItem>(`${BASE}/items/${id}`, { method: "PATCH", body: input });
}

export function deleteItem(id: string) {
  return apiRequest<void>(`${BASE}/items/${id}`, { method: "DELETE" });
}

// ── Service Prices ────────────────────────────────────────────────────────────

export function listServicePrices() {
  return apiRequest<{ items: ServicePrice[] }>(`${BASE}/service-prices`);
}

export function upsertServicePrice(input: {
  service_key: string;
  sale_price: string;
  cost_price: string;
}) {
  return apiRequest<ServicePrice>(`${BASE}/service-prices`, { method: "PUT", body: input });
}
