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

// ── Sales module ──────────────────────────────────────────────────────────────

export const PROJECT_STATUSES = ["active", "completed", "cancelled", "on_hold"] as const;
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

export type Project = {
  id: string;
  company_id: string;
  customer_id: string;
  name: string;
  project_type: string | null;
  address: string | null;
  notes: string | null;
  assigned_to: string | null;
  status: ProjectStatus;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export const QUOTE_STATUSES = ["draft", "sent", "negotiation", "accepted", "rejected", "expired"] as const;
export type QuoteStatus = (typeof QUOTE_STATUSES)[number];

export type Quote = {
  id: string;
  company_id: string;
  project_id: string;
  quote_number: string;
  version: number;
  status: QuoteStatus;
  currency: string;
  price_list_id: string | null;
  valid_until: string | null;
  vat_rate: string;
  discount_type: "none" | "percentage" | "fixed";
  discount_value: string;
  subtotal_gross: string;
  discount_amount: string;
  subtotal_after_discount: string;
  vat_amount: string;
  total_final: string;
  total_cost: string;
  profit: string;
  internal_notes: string | null;
  customer_notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type QuoteSection = {
  id: string;
  company_id: string;
  quote_id: string;
  name: string;
  sort_order: number;
  notes: string | null;
  total_measured_area: string | null;
  subtotal_sale: string;
  subtotal_cost: string;
  created_at: string;
  updated_at: string;
};

export type QuoteSectionMeasurement = {
  id: string;
  company_id: string;
  section_id: string;
  quote_id: string;
  sort_order: number;
  label: string | null;
  length_mm: string | null;
  width_mm: string | null;
  thickness_mm: string | null;
  quantity: number;
  area_m2: string | null;
  waste_pct: string;
  required_area_m2: string | null;
  override_required_area: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export const QUOTE_ITEM_TYPES = [
  "material",
  "wall_cladding",
  "vanity",
  "backsplash",
  "edge_profile",
  "sink_cutout",
  "cooktop_cutout",
  "faucet_hole",
  "installation",
  "transport",
  "crane",
  "other",
] as const;
export type QuoteItemType = (typeof QUOTE_ITEM_TYPES)[number];

export type QuoteSectionItem = {
  id: string;
  company_id: string;
  section_id: string;
  quote_id: string;
  item_type: QuoteItemType;
  sort_order: number;
  description: string;
  material_id: string | null;
  slab_id: string | null;
  quantity: string;
  unit: string;
  unit_sale_price: string;
  unit_cost_price: string;
  line_total_sale: string;
  line_total_cost: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type ServicePrice = {
  id: string;
  company_id: string;
  service_key: string;
  sale_price: string;
  cost_price: string;
  created_at: string;
  updated_at: string;
};

// ── Orders module ─────────────────────────────────────────────────────────────

export const ORDER_STATUSES = [
  "waiting",
  "measuring",
  "approved_for_production",
  "in_production",
  "ready",
  "delivered",
  "installed",
  "completed",
  "cancelled",
] as const;
export type OrderStatus = (typeof ORDER_STATUSES)[number];

export type Order = {
  id: string;
  company_id: string;
  project_id: string;
  customer_id: string;
  quote_id: string;
  order_number: string;
  status: OrderStatus;
  currency: string;
  notes: string | null;
  production_notes: string | null;
  installation_notes: string | null;
  delivery_address: string | null;
  scheduled_production_date: string | null;
  scheduled_installation_date: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancelled_reason: string | null;
  created_by: string | null;
  subtotal_gross: string;
  discount_type: string;
  discount_value: string;
  discount_amount: string;
  subtotal_after_discount: string;
  vat_rate: string;
  vat_amount: string;
  total_final: string;
  total_internal_cost: string;
  total_profit: string;
  created_at: string;
  updated_at: string;
};

export type OrderSection = {
  id: string;
  company_id: string;
  order_id: string;
  name: string;
  sort_order: number;
  notes: string | null;
  total_measured_area: string | null;
  subtotal_sale: string;
  subtotal_cost: string;
  created_at: string;
  updated_at: string;
};

export type OrderItem = {
  id: string;
  company_id: string;
  order_id: string;
  section_id: string;
  item_type: string;
  sort_order: number;
  description: string;
  material_id: string | null;
  slab_id: string | null;
  quantity: string;
  unit: string;
  unit_sale_price: string;
  unit_cost_price: string;
  line_total_sale: string;
  line_total_cost: string;
  notes: string | null;
  production_status: string | null;
  installation_status: string | null;
  created_at: string;
  updated_at: string;
};

export type OrderMeasurement = {
  id: string;
  company_id: string;
  order_id: string;
  section_id: string;
  sort_order: number;
  label: string | null;
  length_mm: string | null;
  width_mm: string | null;
  thickness_mm: string | null;
  quantity: number;
  area_m2: string | null;
  required_area_m2: string | null;
  waste_pct: string;
  override_required_area: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};
