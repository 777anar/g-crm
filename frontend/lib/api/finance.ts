import { apiRequest } from "../api-client";
import type { Expense, Invoice, InvoiceLine, Paginated, Payment } from "../types";

const BASE = "/api/v1/finance";

// ── Invoices ──────────────────────────────────────────────────────────────────

export function listInvoices(
  params: {
    customerId?: string;
    status?: string;
    search?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Invoice>>(`${BASE}/invoices`, {
    searchParams: {
      customer_id: params.customerId,
      status: params.status,
      search: params.search || undefined,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createInvoice(orderId: string, input: { due_date?: string; notes?: string } = {}) {
  return apiRequest<Invoice>(`${BASE}/invoices`, {
    method: "POST",
    body: { order_id: orderId, due_date: input.due_date, notes: input.notes },
  });
}

export function getInvoice(id: string) {
  return apiRequest<Invoice>(`${BASE}/invoices/${id}`);
}

export function getInvoiceForOrder(orderId: string) {
  return apiRequest<Invoice>(`${BASE}/invoices/by-order/${orderId}`);
}

export function updateInvoice(id: string, input: { due_date?: string | null; notes?: string | null }) {
  return apiRequest<Invoice>(`${BASE}/invoices/${id}`, { method: "PATCH", body: input });
}

export function updateInvoiceStatus(id: string, status: string, cancelledReason?: string) {
  return apiRequest<Invoice>(`${BASE}/invoices/${id}/status`, {
    method: "POST",
    body: { status, cancelled_reason: cancelledReason },
  });
}

export function listInvoiceLines(invoiceId: string) {
  return apiRequest<{ items: InvoiceLine[] }>(`${BASE}/invoices/${invoiceId}/lines`);
}

export function listInvoicePayments(invoiceId: string) {
  return apiRequest<{ items: Payment[] }>(`${BASE}/invoices/${invoiceId}/payments`);
}

export function recordPayment(
  invoiceId: string,
  input: { amount: string; method: string; paid_at?: string; reference_note?: string }
) {
  return apiRequest<Payment>(`${BASE}/invoices/${invoiceId}/payments`, { method: "POST", body: input });
}

// ── Expenses ──────────────────────────────────────────────────────────────────

export function listExpenses(
  params: {
    orderId?: string;
    category?: string;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Expense>>(`${BASE}/expenses`, {
    searchParams: {
      order_id: params.orderId,
      category: params.category,
      date_from: params.dateFrom,
      date_to: params.dateTo,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createExpense(input: {
  category: string;
  amount: string;
  expense_date: string;
  order_id?: string;
  description?: string;
  currency?: string;
}) {
  return apiRequest<Expense>(`${BASE}/expenses`, { method: "POST", body: input });
}

export function getExpense(id: string) {
  return apiRequest<Expense>(`${BASE}/expenses/${id}`);
}
