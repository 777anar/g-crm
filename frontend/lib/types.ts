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

export type CompanyUser = {
  id: string;
  full_name: string;
  email: string;
  role: string;
};

export const CUSTOMER_TYPES = ["individual", "business"] as const;
export type CustomerType = (typeof CUSTOMER_TYPES)[number];

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
  type: CustomerType;
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

// ── Tasks & Reminders (Version 1.2) ──────────────────────────────────────────

export const TASK_STATUSES = ["pending", "in_progress", "done", "cancelled"] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_PRIORITIES = ["low", "medium", "high", "urgent"] as const;
export type TaskPriority = (typeof TASK_PRIORITIES)[number];

export const TASK_RECURRENCE_RULES = ["daily", "weekly", "monthly", "yearly"] as const;
export type TaskRecurrenceRule = (typeof TASK_RECURRENCE_RULES)[number];

export type Task = {
  id: string;
  company_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  tags: string[];
  due_date: string | null;
  remind_at: string | null;
  assigned_to: string | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  is_recurring: boolean;
  recurrence_rule: TaskRecurrenceRule | null;
  recurrence_interval: number;
  recurrence_end_date: string | null;
  series_id: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancelled_reason: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export const TASK_NOTIFICATION_TYPES = ["task_assigned", "task_reassigned", "task_reminder", "task_overdue"] as const;
export type TaskNotificationType = (typeof TASK_NOTIFICATION_TYPES)[number];

export type TaskNotification = {
  id: string;
  notification_type: TaskNotificationType;
  title: string;
  message: string;
  task_id: string;
  read_at: string | null;
  created_at: string;
};

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

// Common industry-standard slab thicknesses/sizes, offered as a guided
// dropdown instead of free text so material entry stays structured
// (Brand -> Stone -> Thickness -> Size) ahead of a future official supplier
// catalog import -- these are just everyday defaults, not manufacturer specs.
export const SUGGESTED_THICKNESSES_MM = ["12", "20", "30"] as const;

export const SUGGESTED_SIZES_MM = [
  "3200x1600mm",
  "3000x1400mm",
  "3200x1500mm",
  "2800x1300mm",
  "1600x800mm",
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

// Sprint 4: normalized Thickness/Size options per Stone (Material), replacing
// the single free-text thickness_mm/dimensions columns as the source of
// truth for the Brand -> Stone -> Thickness -> Size selector.
export type MaterialThickness = {
  id: string;
  material_id: string;
  thickness_mm: string;
  sort_order: number;
  created_at: string;
};

export type MaterialSize = {
  id: string;
  material_id: string;
  dimensions: string;
  sort_order: number;
  created_at: string;
};

// Curated brand suggestions for the Brand creation form (Sprint 4) --
// Brand.name stays free text server-side, this is just a starter list.
export const SUPPORTED_BRANDS = [
  "NEOLITH",
  "MARAZZI THE TOP",
  "SAPIENSTONE",
  "INALCO",
  "ANATOLIA",
  "BELENCO",
  "COANTE",
] as const;

// ── Sales module ──────────────────────────────────────────────────────────────

export const PROJECT_STATUSES = ["active", "completed", "cancelled"] as const;
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
  discount_type: "none" | "percent" | "fixed";
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
  "countertop",
  "island",
  "tv_panel",
  "bathroom_furniture",
  "flooring",
  "stairs",
  "table",
  "sink",
  "fireplace",
  "window_sill",
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

// ── Project workspace (Sprint 3: Rooms / Project Items / Measurements / Drawings / Photos) ────

// Full set of room_type values the backend accepts, including legacy ones
// (staircase/exterior) kept only for backward compatibility with Rooms
// saved before Sprint 5 -- not offered in the picker, see PROJECT_ROOM_TYPES.
export const ROOM_TYPES = [
  "kitchen",
  "bathroom",
  "living_room",
  "staircase",
  "exterior",
  "custom",
  "corridor",
  "balcony",
  "facade",
  "yard",
] as const;
export type RoomType = (typeof ROOM_TYPES)[number];

// The curated set offered by the Project workspace's "Məkan" picker
// (Sprint 5's authoritative 8-item list).
export const PROJECT_ROOM_TYPES = [
  "kitchen",
  "bathroom",
  "living_room",
  "corridor",
  "balcony",
  "facade",
  "yard",
  "custom",
] as const;

export type Room = {
  id: string;
  company_id: string;
  project_id: string;
  room_type: RoomType;
  name: string | null;
  notes: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

// The curated set offered by the Project Item ("Məmulat") picker --
// Sprint 5's authoritative 12-item list. "sink" (Sprint 3) is no longer
// offered here but stays valid -- see QUOTE_ITEM_TYPES -- for Items saved
// before Sprint 5.
export const PROJECT_ITEM_TYPES = [
  "countertop",
  "island",
  "vanity",
  "bathroom_furniture",
  "tv_panel",
  "table",
  "wall_cladding",
  "flooring",
  "stairs",
  "fireplace",
  "window_sill",
  "other",
] as const;
export type ProjectItemType = (typeof PROJECT_ITEM_TYPES)[number];

export type ProjectItem = {
  id: string;
  company_id: string;
  project_id: string;
  room_id: string;
  item_type: string;
  name: string | null;
  material_id: string | null;
  material_thickness_id: string | null;
  material_size_id: string | null;
  quantity: string;
  unit: string;
  notes: string | null;
  production_status: string | null;
  installation_status: string | null;
  completion_status: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

// "Təhvil" -- handover to the customer, distinct from production/installation.
export const COMPLETION_STATUSES = ["pending", "delivered", "accepted"] as const;
export type CompletionStatus = (typeof COMPLETION_STATUSES)[number];

export const MEASUREMENT_STATUSES = ["draft", "final"] as const;
export type MeasurementStatus = (typeof MEASUREMENT_STATUSES)[number];

export type ProjectItemMeasurement = {
  id: string;
  company_id: string;
  project_item_id: string;
  revision_number: number;
  status: MeasurementStatus;
  length_mm: string | null;
  width_mm: string | null;
  thickness_mm: string | null;
  quantity: number;
  area_m2: string | null;
  measurer_name: string;
  measured_at: string | null;
  notes: string | null;
  customer_signature_document_id: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export const DRAWING_TYPES = ["dwg", "dxf", "sketch", "pdf"] as const;
export type DrawingType = (typeof DRAWING_TYPES)[number];

export type ProjectItemDrawing = {
  id: string;
  company_id: string;
  project_item_id: string;
  document_id: string;
  drawing_type: DrawingType;
  label: string | null;
  sort_order: number;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectItemPhoto = {
  id: string;
  company_id: string;
  project_item_id: string;
  document_id: string;
  caption: string | null;
  sort_order: number;
  uploaded_by: string | null;
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

// ── Production module ─────────────────────────────────────────────────────────

export const WORK_ORDER_STATUSES = [
  "queued",
  "cutting",
  "polishing",
  "quality_check",
  "completed",
  "cancelled",
] as const;
export type WorkOrderStatus = (typeof WORK_ORDER_STATUSES)[number];

export type WorkOrder = {
  id: string;
  company_id: string;
  order_id: string;
  work_order_number: string;
  status: WorkOrderStatus;
  assigned_to: string | null;
  scheduled_start_date: string | null;
  scheduled_completion_date: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancelled_reason: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkOrderItem = {
  id: string;
  order_item_id: string;
  slab_id: string;
  slab_number: string;
  description: string;
  quantity: string;
  unit: string;
  area_m2: string | null;
};

// ── Installation module ───────────────────────────────────────────────────────

export const CREW_STATUSES = ["active", "inactive"] as const;
export type CrewStatus = (typeof CREW_STATUSES)[number];

export type Crew = {
  id: string;
  company_id: string;
  name: string;
  status: CrewStatus;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type CrewMember = {
  id: string;
  crew_id: string;
  user_id: string;
  is_lead: boolean;
  full_name: string;
  email: string;
};

export const INSTALLATION_JOB_STATUSES = [
  "scheduled",
  "en_route",
  "in_progress",
  "completed",
  "cancelled",
] as const;
export type InstallationJobStatus = (typeof INSTALLATION_JOB_STATUSES)[number];

export type InstallationJob = {
  id: string;
  company_id: string;
  order_id: string;
  job_number: string;
  status: InstallationJobStatus;
  crew_id: string | null;
  scheduled_date: string | null;
  scheduled_time_slot: string | null;
  route_sequence: number | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancelled_reason: string | null;
  notes: string | null;
  completion_notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export const PHOTO_TYPES = ["before", "after", "damage", "signature", "other"] as const;
export type PhotoType = (typeof PHOTO_TYPES)[number];

export type InstallationPhoto = {
  id: string;
  installation_job_id: string;
  document_id: string;
  photo_type: PhotoType;
  caption: string | null;
  sort_order: number;
  created_at: string;
};

export type InstallationNotification = {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  installation_job_id: string | null;
  read_at: string | null;
  created_at: string;
};

// ── Reports module ────────────────────────────────────────────────────────────

export const REPORT_PERIODS = ["7d", "30d", "90d", "12m", "custom"] as const;
export type ReportPeriod = (typeof REPORT_PERIODS)[number];

export type StatusCount = { status: string; count: number };

export type ExecutiveDashboard = {
  date_from: string;
  date_to: string;
  kpis: {
    active_customers: number;
    new_customers: number;
    lost_customers: number;
    leads_captured: number;
    leads_converted: number;
    lead_conversion_rate: number;
    quote_win_rate: number;
    orders_created: number;
    revenue: string;
    profit: string;
    profit_margin_pct: number;
    orders_in_production: number;
    orders_awaiting_installation: number;
  };
  customers_by_status: StatusCount[];
  orders_by_status: StatusCount[];
  revenue_trend: { month: string; revenue: string; profit: string; count: number }[];
};

export type SalesAnalytics = {
  date_from: string;
  date_to: string;
  kpis: {
    total_quotes: number;
    accepted_quotes: number;
    win_rate: number;
    accepted_revenue: string;
    avg_quote_value: string;
  };
  quotes_by_status: StatusCount[];
  revenue_by_project_type: { project_type: string; revenue: string }[];
  top_customers: { customer_id: string; customer_name: string; revenue: string }[];
  monthly_trend: {
    month: string;
    draft: number;
    sent: number;
    negotiation: number;
    accepted: number;
    rejected: number;
    expired: number;
  }[];
};

export type ProductionAnalytics = {
  date_from: string;
  date_to: string;
  kpis: {
    orders_in_production: number;
    orders_ready: number;
    orders_entered_production: number;
    orders_completed_production: number;
    avg_production_cycle_days: number | null;
  };
  order_status_breakdown: StatusCount[];
  item_production_status: StatusCount[];
};

export type InstallationAnalytics = {
  date_from: string;
  date_to: string;
  kpis: {
    jobs_created: number;
    jobs_completed: number;
    jobs_awaiting: number;
    jobs_delayed: number;
    avg_delay_days: number | null;
    avg_installation_hours: number | null;
  };
  job_status_breakdown: StatusCount[];
  daily_installations: { date: string; count: number }[];
  crew_productivity: {
    crew_id: string;
    crew_name: string;
    completed_count: number;
    avg_installation_hours: number | null;
  }[];
};

// ── Finance module ────────────────────────────────────────────────────────────

export const INVOICE_STATUSES = [
  "draft",
  "sent",
  "partially_paid",
  "paid",
  "overdue",
  "cancelled",
] as const;
export type InvoiceStatus = (typeof INVOICE_STATUSES)[number];

export type Invoice = {
  id: string;
  company_id: string;
  order_id: string;
  customer_id: string;
  installation_job_id: string | null;
  invoice_number: string;
  status: InvoiceStatus;
  currency: string;
  subtotal_amount: string;
  total_amount: string;
  amount_paid: string;
  balance_due: string;
  issue_date: string;
  due_date: string | null;
  notes: string | null;
  sent_at: string | null;
  paid_at: string | null;
  cancelled_at: string | null;
  cancelled_reason: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type InvoiceLine = {
  id: string;
  company_id: string;
  invoice_id: string;
  description: string;
  amount: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export const PAYMENT_METHODS = ["cash", "bank_transfer", "card", "check", "other"] as const;
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

export type Payment = {
  id: string;
  company_id: string;
  invoice_id: string;
  amount: string;
  method: PaymentMethod;
  paid_at: string;
  reference_note: string | null;
  recorded_by: string | null;
  created_at: string;
  updated_at: string;
};

export const EXPENSE_CATEGORIES = ["materials", "labor", "transport", "utilities", "rent", "other"] as const;
export type ExpenseCategory = (typeof EXPENSE_CATEGORIES)[number];

export type Expense = {
  id: string;
  company_id: string;
  order_id: string | null;
  category: ExpenseCategory;
  description: string | null;
  amount: string;
  currency: string;
  expense_date: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type FinanceAnalytics = {
  date_from: string;
  date_to: string;
  kpis: {
    revenue: string;
    cost: string;
    profit: string;
    profit_margin_pct: number;
    recognized_revenue: string;
    pipeline_value: string;
    cancelled_value: string;
    orders_count: number;
  };
  monthly_trend: { month: string; revenue: string; cost: string; profit: string; count: number }[];
  revenue_by_currency: { currency: string; revenue: string }[];
};

export type InventoryAnalytics = {
  date_from: string;
  date_to: string;
  kpis: {
    total_slabs: number;
    available_slabs: number;
    reserved_slabs: number;
    in_production_slabs: number;
    sold_slabs: number;
    available_area_m2: string;
    materials_tracked: number;
    materials_out_of_stock: number;
    warehouses_count: number;
  };
  slabs_by_status: StatusCount[];
  available_slabs_by_warehouse: { warehouse: string; count: number }[];
};

// ── Communication Center (Version 2.7) ───────────────────────────────────────

export const CHANNEL_TYPES = ["whatsapp", "instagram", "messenger", "email", "sms", "webhook"] as const;
export type ChannelType = (typeof CHANNEL_TYPES)[number];

export type Channel = {
  id: string;
  company_id: string;
  channel_type: ChannelType;
  display_name: string;
  identifier: string | null;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export const CONVERSATION_STATUSES = ["open", "pending", "closed"] as const;
export type ConversationStatus = (typeof CONVERSATION_STATUSES)[number];

export type Conversation = {
  id: string;
  company_id: string;
  channel_id: string;
  customer_id: string | null;
  lead_id: string | null;
  project_id: string | null;
  quote_id: string | null;
  order_id: string | null;
  external_contact_id: string;
  external_contact_name: string | null;
  status: ConversationStatus;
  assigned_to: string | null;
  tags: string[];
  unread_count: number;
  last_message_at: string | null;
  last_message_preview: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export const MESSAGE_DIRECTIONS = ["inbound", "outbound"] as const;
export type MessageDirection = (typeof MESSAGE_DIRECTIONS)[number];

export const MESSAGE_TYPES = ["text", "image", "document", "audio", "video", "template"] as const;
export type MessageType = (typeof MESSAGE_TYPES)[number];

export type Message = {
  id: string;
  company_id: string;
  conversation_id: string;
  direction: MessageDirection;
  sender_type: "customer" | "agent" | "system";
  sender_user_id: string | null;
  message_type: MessageType;
  body: string | null;
  template_id: string | null;
  external_message_id: string | null;
  status: "received" | "queued" | "sent" | "delivered" | "read" | "failed";
  created_at: string;
  updated_at: string;
};

export type MessageAttachment = {
  id: string;
  message_id: string;
  document_id: string;
  file_name: string | null;
  created_at: string;
};

export type ConversationNote = {
  id: string;
  conversation_id: string;
  body: string;
  created_by: string | null;
  created_at: string;
};

export type MessageTemplate = {
  id: string;
  company_id: string;
  name: string;
  channel_type: ChannelType | null;
  shortcut: string | null;
  body: string;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

// ── Real Integrations (Version 2.9) ──────────────────────────────────────────

export const PROVIDER_NAMES = [
  "meta_whatsapp",
  "meta_instagram",
  "meta_messenger",
  "smtp",
  "twilio_sms",
  "webhook",
] as const;
export type ProviderName = (typeof PROVIDER_NAMES)[number];

export const PROVIDERS_FOR_CHANNEL_TYPE: Record<ChannelType, ProviderName[]> = {
  whatsapp: ["meta_whatsapp"],
  instagram: ["meta_instagram"],
  messenger: ["meta_messenger"],
  email: ["smtp"],
  sms: ["twilio_sms"],
  webhook: ["webhook"],
};

export const HEALTH_STATUSES = ["unknown", "ok", "error"] as const;
export type HealthStatus = (typeof HEALTH_STATUSES)[number];

export type ChannelCredential = {
  id: string;
  channel_id: string;
  provider: ProviderName;
  masked_config: Record<string, unknown>;
  has_webhook_secret: boolean;
  health_status: HealthStatus;
  last_checked_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export const QUEUE_STATUSES = ["pending", "processing", "sent", "failed"] as const;
export type QueueStatus = (typeof QUEUE_STATUSES)[number];

export type MessageQueueEntry = {
  id: string;
  message_id: string;
  channel_id: string;
  status: QueueStatus;
  attempts: number;
  max_attempts: number;
  next_attempt_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type IntegrationLogEntry = {
  id: string;
  channel_id: string | null;
  provider: string;
  direction: "outbound" | "inbound";
  action: string;
  success: boolean;
  status_code: number | null;
  signature_valid: boolean | null;
  error_message: string | null;
  duration_ms: number | null;
  payload: unknown;
  created_at: string;
};

// ── AI Sales Assistant (Version 2.8) ─────────────────────────────────────────

export const AI_PROVIDERS = ["mock", "openai", "anthropic", "gemini", "ollama", "azure_openai"] as const;
export type AIProviderName = (typeof AI_PROVIDERS)[number];

export const AI_ANALYSIS_KINDS = ["lead", "conversation", "quote", "task"] as const;
export type AIAnalysisKind = (typeof AI_ANALYSIS_KINDS)[number];

export const AI_RECOMMENDATION_STATUSES = ["pending", "accepted", "rejected", "edited"] as const;
export type AIRecommendationStatus = (typeof AI_RECOMMENDATION_STATUSES)[number];

export const AI_RECOMMENDATION_TYPES = [
  "lead_score",
  "win_probability",
  "priority_recommendation",
  "next_best_action",
  "follow_up_recommendation",
  "duplicate_lead",
  "similar_customer",
  "missing_info",
  "lead_quality_explanation",
  "conversation_language",
  "conversation_intent",
  "conversation_sentiment",
  "conversation_urgency",
  "conversation_summary",
  "conversation_extraction",
  "conversation_link_suggestion",
  "product_recommendation",
  "cross_sell_suggestion",
  "upsell_suggestion",
  "discount_recommendation",
  "margin_risk_detection",
  "price_anomaly_detection",
  "delivery_complexity_estimate",
  "task_suggestion",
  "reminder_suggestion",
  "assignee_suggestion",
  "task_priority_suggestion",
  "overdue_risk",
] as const;
export type AIRecommendationType = (typeof AI_RECOMMENDATION_TYPES)[number];

export type AIRecommendation = {
  id: string;
  company_id: string;
  analysis_kind: AIAnalysisKind;
  recommendation_type: AIRecommendationType;
  related_entity_type: string | null;
  related_entity_id: string | null;
  provider: string;
  model: string;
  prompt: string;
  response: Record<string, any>;
  confidence_score: number | null;
  execution_time_ms: number | null;
  summary: string | null;
  status: AIRecommendationStatus;
  edited_response: Record<string, any> | null;
  requested_by: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AIDashboard = {
  lead_score_distribution: Record<string, number>;
  avg_win_probability: number | null;
  pipeline_health: {
    active_pipeline_count: number;
    stalled_count: number;
    stalled_pct: number;
  };
  at_risk_customers: Array<{
    recommendation_id: string;
    related_entity_type: string | null;
    related_entity_id: string | null;
    recommendation_type: string;
    summary: string | null;
  }>;
  follow_up_recommendations: Array<{
    recommendation_id: string;
    related_entity_type: string | null;
    related_entity_id: string | null;
    summary: string | null;
    due_in_days: number | null;
  }>;
  daily_recommendations: Array<{
    recommendation_id: string;
    recommendation_type: string;
    summary: string | null;
    created_at: string;
  }>;
  recent_activity: Array<{
    recommendation_id: string;
    recommendation_type: string;
    analysis_kind: string;
    status: string;
    provider: string;
    summary: string | null;
    created_at: string;
    reviewed_at: string | null;
  }>;
  usage_stats: {
    total_recommendations: number;
    status_counts: Record<string, number>;
    provider_counts: Record<string, number>;
    acceptance_rate: number | null;
    avg_execution_time_ms: number | null;
  };
};
