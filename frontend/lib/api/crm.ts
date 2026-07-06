import { apiRequest } from "../api-client";
import type {
  Activity,
  Attachment,
  Customer,
  CustomerProfile,
  CustomerStatus,
  Lead,
  Paginated,
  Task,
  TaskNotification,
} from "../types";

export function listCustomers(
  params: {
    includeArchived?: boolean;
    status?: CustomerStatus;
    leadSource?: string;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Customer>>("/api/v1/crm/customers", {
    searchParams: {
      include_archived: params.includeArchived,
      status: params.status,
      lead_source: params.leadSource,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
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
  phone?: string;
  whatsapp?: string;
  instagram?: string;
  facebook?: string;
  email?: string;
  address?: string;
  company_name?: string;
  notes?: string;
  status?: CustomerStatus;
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

export function listLeads(
  params: { sourceChannel?: string; status?: string; search?: string; sort?: string; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<Lead>>("/api/v1/crm/leads", {
    searchParams: {
      source_channel: params.sourceChannel,
      status: params.status,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
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

// ── Tasks & Reminders (Version 1.2) ──────────────────────────────────────────

export function listTasks(
  params: {
    assignedTo?: string;
    status?: string;
    priority?: string;
    relatedEntityType?: string;
    relatedEntityId?: string;
    dueBefore?: string;
    dueAfter?: string;
    excludeTerminal?: boolean;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Task>>("/api/v1/crm/tasks", {
    searchParams: {
      assigned_to: params.assignedTo,
      status: params.status,
      priority: params.priority,
      related_entity_type: params.relatedEntityType,
      related_entity_id: params.relatedEntityId,
      due_before: params.dueBefore,
      due_after: params.dueAfter,
      exclude_terminal: params.excludeTerminal,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getTask(id: string) {
  return apiRequest<Task>(`/api/v1/crm/tasks/${id}`);
}

export function listTaskSeries(id: string) {
  return apiRequest<{ items: Task[] }>(`/api/v1/crm/tasks/${id}/series`);
}

export type CreateTaskInput = {
  title: string;
  description?: string;
  priority?: string;
  due_date?: string;
  remind_at?: string;
  assigned_to?: string;
  tags?: string[];
  related_entity_type?: string;
  related_entity_id?: string;
  is_recurring?: boolean;
  recurrence_rule?: string;
  recurrence_interval?: number;
  recurrence_end_date?: string;
};

export function createTask(input: CreateTaskInput) {
  return apiRequest<Task>("/api/v1/crm/tasks", { method: "POST", body: input });
}

export function updateTask(id: string, input: Partial<CreateTaskInput>) {
  return apiRequest<Task>(`/api/v1/crm/tasks/${id}`, { method: "PATCH", body: input });
}

export function updateTaskStatus(id: string, status: string, cancelledReason?: string) {
  return apiRequest<Task>(`/api/v1/crm/tasks/${id}/status`, {
    method: "POST",
    body: { status, cancelled_reason: cancelledReason },
  });
}

export function deleteTask(id: string) {
  return apiRequest<void>(`/api/v1/crm/tasks/${id}`, { method: "DELETE" });
}

export function listTaskNotifications(params: { unreadOnly?: boolean } = {}) {
  return apiRequest<{ items: TaskNotification[] }>("/api/v1/crm/task-notifications", {
    searchParams: { unread_only: params.unreadOnly },
  });
}

export function checkTaskReminders() {
  return apiRequest<{ items: TaskNotification[] }>("/api/v1/crm/task-notifications/check", { method: "POST" });
}

export function markTaskNotificationRead(id: string) {
  return apiRequest<TaskNotification>(`/api/v1/crm/task-notifications/${id}/read`, { method: "POST" });
}
