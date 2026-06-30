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

// --- Stone Catalog (Version 2.0) -------------------------------------------

export const ENTITY_STATUSES = ["active", "hidden"] as const;
export type EntityStatus = (typeof ENTITY_STATUSES)[number];

export const MATERIAL_STATUSES = ["active", "hidden"] as const;
export type MaterialStatus = (typeof MATERIAL_STATUSES)[number];

export const SLAB_STATUSES = ["available", "reserved", "sold", "in_production", "scrap"] as const;
export type SlabStatus = (typeof SLAB_STATUSES)[number];

export const IMAGE_TYPES = ["gallery", "thumbnail", "bookmatch_left", "bookmatch_right"] as const;
export type ImageType = (typeof IMAGE_TYPES)[number];

export const DOCUMENT_TYPES = ["technical_pdf", "installation_guide", "cleaning_guide"] as const;
export type CatalogDocumentType = (typeof DOCUMENT_TYPES)[number];

export const SUGGESTED_MATERIAL_TYPES = [
  "Sintered Stone",
  "Porcelain",
  "Quartz",
  "Natural Marble",
  "Natural Granite",
  "Dekton",
  "Ceramic",
] as const;

export type Brand = {
  id: string;
  name: string;
  description: string | null;
  logo_document_id: string | null;
  status: EntityStatus;
  created_at: string;
  updated_at: string;
};

export type Collection = {
  id: string;
  brand_id: string;
  name: string;
  description: string | null;
  status: EntityStatus;
  created_at: string;
  updated_at: string;
};

export type Material = {
  id: string;
  brand_id: string;
  collection_id: string | null;
  name: string;
  material_type: string | null;
  color: string | null;
  finish: string | null;
  thickness_mm: string | null;
  dimensions: string | null;
  country_of_origin: string | null;
  description: string | null;
  status: MaterialStatus;
  created_at: string;
  updated_at: string;
};

export type Warehouse = {
  id: string;
  name: string;
  address: string | null;
  status: EntityStatus;
  created_at: string;
  updated_at: string;
};

export type Slab = {
  id: string;
  material_id: string;
  warehouse_id: string;
  slab_number: string;
  lot_number: string | null;
  barcode: string | null;
  rack_location: string | null;
  length_mm: string | null;
  width_mm: string | null;
  area_m2: string | null;
  weight_kg: string | null;
  status: SlabStatus;
  created_at: string;
  updated_at: string;
};

export type PriceList = {
  id: string;
  name: string;
  currency: string;
  is_default: boolean;
  status: EntityStatus;
  created_at: string;
  updated_at: string;
};

export type PriceListEntry = {
  id: string;
  price_list_id: string;
  material_id: string;
  cost_price: string;
  sale_price: string;
};

export type MaterialImage = {
  id: string;
  material_id: string;
  document_id: string;
  image_type: ImageType;
  sort_order: number;
  created_at: string;
};

export type MaterialDocumentAsset = {
  id: string;
  material_id: string;
  document_id: string;
  document_type: CatalogDocumentType;
  created_at: string;
};
