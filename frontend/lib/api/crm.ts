import { apiRequest } from "../api-client";
import type { Activity, Attachment, Customer, CustomerProfile, Lead, Paginated } from "../types";

export function listCustomers(params: { includeArchived?: boolean } = {}) {
  return apiRequest<Paginated<Customer>>("/api/v1/crm/customers", {
    searchParams: { include_archived: params.includeArchived },
  });
}

export function getCustomer(id: string) {
  return apiRequest<Customer>(`/api/v1/crm/customers/${id}`);
}

export function getCustomerProfile(id: string) {
  return apiRequest<CustomerProfile>(`/api/v1/crm/customers/${id}/profile`);
}

export type CreateCustomerInput = {
  name: string;
  type: "individual" | "business";
  lead_source?: string;
  advertising_campaign?: string;
  tags?: string[];
  contact?: { full_name: string; email?: string; phone?: string };
};

export function createCustomer(input: CreateCustomerInput) {
  return apiRequest<Customer>("/api/v1/crm/customers", { method: "POST", body: input });
}

export function updateCustomer(id: string, input: Partial<CreateCustomerInput>) {
  return apiRequest<Customer>(`/api/v1/crm/customers/${id}`, { method: "PATCH", body: input });
}

export function archiveCustomer(id: string) {
  return apiRequest<Customer>(`/api/v1/crm/customers/${id}`, { method: "DELETE" });
}

export function addCustomerNote(id: string, body: string) {
  return apiRequest<Activity>(`/api/v1/crm/customers/${id}/notes`, { method: "POST", body: { body } });
}

export function uploadCustomerAttachment(customerId: string, file: File) {
  const formData = new FormData();
  formData.append("module", "crm");
  formData.append("related_entity_type", "customer");
  formData.append("related_entity_id", customerId);
  formData.append("file", file);
  return apiRequest<Attachment>("/api/v1/core/documents", { method: "POST", formData });
}

export function listLeads(params: { sourceChannel?: string; status?: string } = {}) {
  return apiRequest<Paginated<Lead>>("/api/v1/crm/leads", {
    searchParams: { source_channel: params.sourceChannel, status: params.status },
  });
}

export type CreateLeadInput = {
  full_name: string;
  source_channel: string;
  email?: string;
  phone?: string;
  campaign?: string;
};

export function createLead(input: CreateLeadInput) {
  return apiRequest<Lead>("/api/v1/crm/leads", { method: "POST", body: input });
}

export function convertLead(id: string) {
  return apiRequest<{ customer_id: string; contact_id: string | null }>(`/api/v1/crm/leads/${id}/convert`, {
    method: "POST",
  });
}
