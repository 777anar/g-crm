export type Money = { amount: string; currency: string };

export type ApiError = {
  error: {
    code: string;
    message: string;
    details: { field: string; issue: string }[];
    request_id: string;
  };
};

export type CompanyMembership = { id: string; name: string; role: string };

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  companies: CompanyMembership[];
};

export type Company = {
  id: string;
  name: string;
  slug: string;
  currency: string;
  locale: string;
  logo_url: string | null;
  enabled_modules: string[];
};

export const CUSTOMER_STATUSES = [
  "new_inquiry",
  "contacted",
  "measurement_scheduled",
  "measurement_completed",
  "preparing_quote",
  "quote_sent",
  "waiting_for_decision",
  "approved",
  "payment_received",
  "in_production",
  "installation_scheduled",
  "installed",
  "completed",
  "lost",
] as const;
export type CustomerStatus = (typeof CUSTOMER_STATUSES)[number];

export type Customer = {
  id: string;
  name: string;
  type: "individual" | "business";
  primary_contact_id: string | null;
  assigned_manager_id: string | null;
  lead_source: string | null;
  advertising_campaign: string | null;
  phone: string | null;
  whatsapp: string | null;
  instagram: string | null;
  facebook: string | null;
  email: string | null;
  address: string | null;
  company_name: string | null;
  notes: string | null;
  status: CustomerStatus;
  tags: string[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type Contact = { id: string; full_name: string; email: string | null; phone: string | null };

export type Activity = { id: string; type: string; body: string; created_by: string; created_at: string };

export type Attachment = { id: string; storage_path: string; mime_type: string; created_at: string };

export type CustomerProfile = {
  customer: Customer;
  contacts: Contact[];
  attachments: Attachment[];
  timeline: Activity[];
  projects: Record<string, unknown>[];
  quotes: Record<string, unknown>[];
  orders: Record<string, unknown>[];
  payments: Record<string, unknown>[];
};

export const LEAD_SOURCE_CHANNELS = [
  "instagram",
  "facebook",
  "messenger",
  "whatsapp",
  "phone_call",
  "website",
  "office_visit",
  "referral",
  "other",
] as const;
export type LeadSourceChannel = (typeof LEAD_SOURCE_CHANNELS)[number];

export type Lead = {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  source_channel: LeadSourceChannel;
  campaign: string | null;
  status: "new" | "contacted" | "qualified" | "converted" | "disqualified";
  assigned_manager_id: string | null;
  converted_customer_id: string | null;
  created_at: string;
};

export type Paginated<T> = { items: T[]; next_cursor: string | null };
