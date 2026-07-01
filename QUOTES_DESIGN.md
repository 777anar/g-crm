# G-STONE ERP — Quotes Module Design

_Author: Claude Sonnet 4.6_
_Date: 2026-07-01_
_Status: FROZEN — approved and ready for implementation. No further design changes._
_Depends on: CRM module (Customer, Lead), Stone Catalog module (Material, Slab, Price List)_

---

## 1. Purpose

The Quotes module closes the gap between "a customer wants stone" and "we have a real priced offer on paper." Today a customer reaching the "Quote Sent" stage in the CRM pipeline has nothing behind it — a rep is typing numbers into a spreadsheet or writing them on paper. This module replaces that with:

- A structured, **multi-section** quote drawn entirely from real Catalog data — sections mirror the actual spaces on the job site (Kitchen, Island, Master Bathroom, Staircase, Outdoor, etc.)
- A Project entity that ties multiple quotes to a single job site
- A professional, company-branded PDF that preserves the section hierarchy the customer recognises from the site visit
- Full cost/profit visibility for management that does not appear on the customer PDF
- An audit trail and event hook (`QuoteCreated`, `QuoteAccepted`, `QuoteDeclined`) that downstream modules (Orders, Production) will subscribe to

---

## 2. Business Workflow

### 2.1 The full lifecycle

```
LEAD captured (Instagram / Facebook / WhatsApp / Manual)
  │
  ▼
CUSTOMER created (from lead conversion or direct entry)
  │
  ▼
PROJECT created (a specific job site — "Mirəli's Kitchen", "Əliəkbər Villa – Bathroom 2")
  │
  │  Projects are first-class business objects with their own top-level module
  │  at /sales/projects. A project is the central hub that will eventually
  │  contain: Quotes, Orders, Measurements, Production, Installation, Payments,
  │  Documents, and Photos. Every business process revolves around the Project.
  │
  │  A project has a type: Kitchen / Bathroom / Commercial / Other.
  │  A project has an address, site notes, and an assigned rep.
  │  A customer may have multiple concurrent projects.
  │
  ▼
QUOTE drafted (one project may have multiple quote versions)
  │
  │  The rep creates one or more named sections mirroring the job's physical
  │  spaces (Kitchen, Island, Master Bathroom, Staircase, Outdoor, etc.).
  │  Within each section the rep selects materials, assigns specific slabs,
  │  adds service items (edge profile, cutouts, holes, cladding, installation),
  │  and adds logistics (transport, crane) at the quote level.
  │  Each section computes its own subtotal. The quote totals all sections,
  │  applies a single discount and VAT, and produces the final price.
  │  Default service prices are pulled from company settings and may be
  │  overridden per item. The system recomputes totals live as items change.
  │
  ├─► DRAFT       — being built, not yet sent to customer
  ├─► SENT        — PDF delivered to customer (CRM pipeline → "Quote Sent")
  │                  Any edit after SENT automatically creates a new version.
  │                  The sent version is never overwritten.
  ├─► NEGOTIATION — customer is negotiating; further revisions expected
  ├─► ACCEPTED    — customer confirms (CRM pipeline → "Won")
  │                  Slabs are reserved (available → reserved) at this point.
  │                  Triggers OrderCreated event for the Orders module.
  ├─► REJECTED    — customer walks away (CRM pipeline → "Lost")
  │                  Any reserved slabs are released back to available.
  └─► EXPIRED     — valid_until date has passed without a decision
                     Any reserved slabs are released back to available.
```

### 2.2 Versioning

A quote in `draft` status may be freely edited. The moment a quote is marked `sent`, it becomes **immutable** — it is a legal offer that was delivered to a customer.

Any subsequent edit (rep opens the quote and changes a line item, or changes the discount) automatically creates a new version (`v2`, `v3`, …) with status `draft`, leaving the previously sent version intact and unchanged.

All versions belong to the same Project. The latest active version (highest version number that is not `rejected` or `expired`) is the "working quote" for that project.

This gives the rep a full paper trail ("We originally quoted 4,200 AZN in v1; the customer negotiated to 3,900 AZN in v2, which was accepted.")

**Trigger for auto-versioning:** any mutation of a quote that is in status `sent`, `negotiation`, or `accepted` automatically creates a new version in `draft` status. The original quote's status is unchanged.

### 2.3 CRM pipeline integration

| Quote event | CRM customer status update |
|---|---|
| Quote status → SENT | Customer pipeline → "Quote Sent" |
| Quote status → NEGOTIATION | Customer pipeline → "Negotiation" |
| Quote status → ACCEPTED | Customer pipeline → "Won" |
| Quote status → REJECTED | Customer pipeline → "Lost" |
| Quote status → EXPIRED | Customer pipeline → "Lost" |

The pipeline status is updated automatically via the event bus (`QuoteStatusChanged`), so reps do not need to update the CRM manually.

---

## 3. Data Model

### 3.1 Project

A Project represents one physical job site or renovation scope. It is the container for all quotes related to that scope.

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK | multi-tenancy |
| customer_id | UUID FK | → CRM customers |
| name | VARCHAR(200) | "Mirəli's Kitchen", "Villa Bağça – Master Bath" |
| project_type | ENUM | `kitchen`, `bathroom`, `commercial`, `stairs`, `fireplace`, `other` |
| address | TEXT | job site address |
| notes | TEXT | internal site notes (access, parking, floor level, lift available) |
| assigned_to | UUID FK | → users (rep responsible) |
| status | ENUM | `active`, `completed`, `cancelled` |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

One customer → many projects. One project → many quote versions.

### 3.2 Quote (header)

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK | |
| project_id | UUID FK | → projects |
| customer_id | UUID FK | denormalized from project for fast filtering |
| version | INTEGER | 1, 2, 3 … increments per project |
| quote_number | VARCHAR(50) | human-readable, e.g. "QT-2026-0042-v1" |
| status | ENUM | `draft`, `sent`, `negotiation`, `accepted`, `rejected`, `expired` |
| currency | VARCHAR(3) | "AZN", "USD", "EUR" — defaults to company default |
| price_list_id | UUID FK | which Price List to pull unit prices from |
| valid_until | DATE | offer expiry date |
| internal_notes | TEXT | never on PDF |
| customer_notes | TEXT | appears on PDF as "Notes" section |
| prepared_by | UUID FK | → users |
| sent_at | TIMESTAMPTZ | null until sent |
| accepted_at | TIMESTAMPTZ | null until accepted |
| declined_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Computed totals (stored, not generated at query time):**

The quote header aggregates across all its sections. When any section item changes, the parent section's `subtotal_sale` / `subtotal_cost` is recomputed first, then the quote header totals are recomputed from the section subtotals.

| Field | Type | Notes |
|---|---|---|
| subtotal_gross | NUMERIC(14,2) | Σ section.subtotal_sale across all sections (including the logistics section) |
| discount_type | ENUM | `none`, `percent`, `fixed` |
| discount_value | NUMERIC(14,2) | the % or fixed amount |
| discount_amount | NUMERIC(14,2) | computed: how much is knocked off subtotal_gross |
| subtotal_after_discount | NUMERIC(14,2) | subtotal_gross − discount_amount |
| vat_rate | NUMERIC(5,2) | copied from company settings at quote creation time; editable per quote |
| vat_amount | NUMERIC(14,2) | subtotal_after_discount × (vat_rate / 100) |
| total_final | NUMERIC(14,2) | subtotal_after_discount + vat_amount — this is what the customer pays |
| total_internal_cost | NUMERIC(14,2) | Σ section.subtotal_cost across all sections; never on PDF |
| total_profit | NUMERIC(14,2) | subtotal_after_discount − total_internal_cost; never on PDF |
| profit_margin_pct | NUMERIC(5,2) | total_profit / subtotal_after_discount × 100; never on PDF |

### 3.3 Quote Sections

A quote is composed of one or more **named sections**. Each section represents a distinct physical space or scope on the job site. The rep creates, names, and orders sections freely.

Examples of section names: Kitchen, Island, Master Bathroom, Bathroom 2, Staircase, Fireplace Surround, Outdoor Terrace, Reception Desk.

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| quote_id | UUID FK | → sales_quotes |
| company_id | UUID FK | multi-tenancy |
| name | VARCHAR(200) | free text: "Kitchen", "Island", "Master Bathroom", etc. |
| sort_order | INTEGER | display sequence in the quote and on the PDF |
| notes | TEXT | internal notes for this section; never on PDF |
| total_measured_area | NUMERIC(10,4) | Σ measurement.required_area across all measurement rows; auto-updated when measurements change; null if no measurements entered |
| subtotal_sale | NUMERIC(14,2) | Σ line_total_sale for all items in this section; recomputed on any item change |
| subtotal_cost | NUMERIC(14,2) | Σ line_total_cost for all items in this section; never on PDF |

There is no fixed taxonomy of section names — reps name them freely to match the real job. A quote for a full apartment may have five sections; a simple kitchen quote may have one.

Each section optionally holds one or more **measurement rows** (see §3.4). The measurements drive the section's `total_measured_area`, which the rep uses to set the quantity on material items. Measurements are stored separately so they can be reused by Production and Installation without touching the pricing layer.

### 3.4 Quote Section Measurements

Each section may optionally contain one or more **measurement rows**. A measurement row represents one distinct piece (or a group of identical pieces) within that physical space. Multiple rows in the same section are independent — e.g. a Kitchen section may have one row for the countertop and a second row for the window sill.

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| section_id | UUID FK | → sales_quote_sections |
| quote_id | UUID FK | denormalized for fast filtering |
| company_id | UUID FK | |
| sort_order | INTEGER | display sequence within the section's measurement block |
| label | VARCHAR(200) | optional description of this piece: "Countertop", "Window Sill", "Waterfall Side" |
| length_mm | NUMERIC(10,1) | length in millimetres |
| width_mm | NUMERIC(10,1) | width in millimetres |
| thickness_mm | NUMERIC(6,1) | thickness in millimetres (informational; does not affect area calculation) |
| quantity | INTEGER | number of identical pieces; default 1 |
| area_m2 | NUMERIC(10,4) | **computed, stored**: `length_mm × width_mm × quantity / 1_000_000`; auto-recalculated when dimensions or quantity change |
| waste_pct | NUMERIC(5,2) | waste allowance in percent (e.g. 10.00 for 10%); default from company settings |
| required_area_m2 | NUMERIC(10,4) | **computed, stored**: `area_m2 × (1 + waste_pct / 100)`; auto-recalculated; **rep may override** |
| override_required_area | BOOLEAN | true if the rep has manually set required_area_m2, suppressing auto-recalculation |
| notes | TEXT | internal notes on this piece; never on PDF |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Computation rules:**

```
area_m2          = length_mm × width_mm × quantity / 1_000_000
required_area_m2 = area_m2 × (1 + waste_pct / 100)
                   — unless override_required_area is true,
                     in which case required_area_m2 is exactly what the rep typed
```

When any measurement row changes, the parent section's `total_measured_area` is recomputed:

```
section.total_measured_area = Σ measurement.required_area_m2
                               for all measurement rows in this section
```

The rep uses `section.total_measured_area` as a reference when setting the `quantity` field on a material line item in §3.5. The system does **not** auto-fill the material quantity — this is a deliberate choice, since the rep may price more or less stone than the raw measurement (e.g. they may quote a full slab even if the required area is slightly smaller). The measurement is an informational reference, not a constraint.

**Downstream use:** `sales_quote_section_measurements` rows are read directly by the Production and Installation modules once a quote is accepted. They never need to reenter dimensions — the measurement data already on record is the source of truth for cutting orders and installation scheduling.

**Default waste %:** configurable per company in company settings (`default_waste_pct`; e.g. 10%). The rep may override per measurement row.

### 3.5 Quote Section Items

Every line item belongs to exactly one section. Within a section, items are typed by `item_type` — this controls which fields are relevant, what default price to look up, and how the item is labelled on the PDF.

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| section_id | UUID FK | → sales_quote_sections |
| quote_id | UUID FK | denormalized for fast filtering |
| company_id | UUID FK | |
| item_type | ENUM | see §3.5 |
| sort_order | INTEGER | display sequence within the section |
| description | VARCHAR(500) | shown on PDF; pre-filled by item_type, editable |
| material_id | UUID FK nullable | → catalog_materials (required for material/cladding/vanity/backsplash types) |
| slab_id | UUID FK nullable | → catalog_slabs (optional; null = unspecified slab of this material) |
| quantity | NUMERIC(10,3) | m², linear meters, or unit count — interpretation depends on item_type |
| unit | ENUM | `m2`, `lm`, `unit` |
| unit_sale_price | NUMERIC(14,2) | copied at add time from Price List or company service defaults; editable |
| unit_cost_price | NUMERIC(14,2) | copied at add time; editable; never on PDF |
| line_total_sale | NUMERIC(14,2) | quantity × unit_sale_price |
| line_total_cost | NUMERIC(14,2) | quantity × unit_cost_price; never on PDF |
| notes | TEXT | internal note on this item; never on PDF |

### 3.6 Item Types

`item_type` determines what an item is, its default unit, its default price source, and how it is labelled on the PDF.

| item_type | PDF label | Default unit | Price source |
|---|---|---|---|
| `material` | Stone Material | m² | Catalog Price List (sale + cost) |
| `wall_cladding` | Wall Cladding | m² | Catalog Price List (sale + cost) |
| `vanity` | Vanity Top | m² | Catalog Price List (sale + cost) |
| `backsplash` | Backsplash | m² | Catalog Price List (sale + cost) |
| `edge_profile` | Edge Profile | lm | Company service default (`edge_profile_per_lm`) |
| `sink_cutout` | Sink Cutout | unit | Company service default (`sink_cutout`) |
| `cooktop_cutout` | Cooktop Cutout | unit | Company service default (`cooktop_cutout`) |
| `faucet_hole` | Faucet Holes | unit | Company service default (`faucet_hole`) |
| `installation` | Installation | m² | Company service default (`installation_per_m2`); can be switched to `unit` for flat fee |
| `transport` | Transport | unit | Company service default (`transport`) |
| `crane` | Crane / Lifting | unit | Company service default (`crane`) |
| `other` | Other | unit | Manual entry required |

**Rules:**
- `material`, `wall_cladding`, `vanity`, `backsplash` require a `material_id`; optionally a `slab_id`.
- All other types have no `material_id` — description is free text (e.g. "Bullnose 2cm edge profile", "Undermount sink").
- `transport` and `crane` may appear in any section or at the quote level (see §3.6).
- A section may contain multiple items of the same type (e.g. two `material` rows for a countertop + a waterfall edge in different materials; two `edge_profile` rows for different profile types at different unit prices).

### 3.7 Quote-Level Items

`transport` and `crane` are logistics items that apply to the whole job, not to a specific space. They are stored as items in a reserved system section named **"Delivery & Logistics"** that is always last in the PDF. The rep may add them via a one-click toggle in the quote builder; they are pre-filled from company service defaults.

### 3.8 Slab Reservation

Slab reservations are tied to the `accepted` status only — a sent or negotiating quote does not guarantee a sale and must not lock inventory.

| Quote event | Slab effect |
|---|---|
| Slab assigned in `draft` / `sent` / `negotiation` | No change to slab status (`available` stays `available`) |
| Quote → `accepted` | All assigned slabs: `available` → `reserved` via `SlabReserved` event |
| Quote → `rejected` or `expired` | All reserved slabs: `reserved` → `available` via `SlabReleased` event |
| Order created from accepted quote | Slabs: `reserved` → `sold` (handled by the Orders module) |

If two reps both have the same slab on quotes that reach `accepted` simultaneously, the system checks slab availability at the moment of acceptance and rejects the second acceptance with a conflict error, prompting the rep to reassign the slab.

---

## 4. Pricing Logic

### 4.1 Price resolution

When a rep adds a line item, unit prices are resolved in this order:

**Material items:**
1. Pull `sale_price` and `cost_price` from the Price List entry for this material (using the quote's `price_list_id`).
2. If no Price List entry exists, leave the price fields blank — the rep must enter manually before sending.

**Work and logistics items (edge profile, cutouts, transport, crane, installation, etc.):**
1. Pull the default price from company settings (`default_service_prices`), keyed by the service type (e.g. `transport`, `installation_per_m2`, `sink_cutout`, `faucet_hole`, `cooktop_cutout`, `edge_profile_per_lm`, `crane`).
2. The rep may override the price for any individual line item without changing the company default.
3. Company service price defaults are managed by Owners at `/settings/service-prices`.

**In all cases:**
Prices are **copied into the section item at add time** — subsequent changes to the Price List or company defaults do not retroactively change a quote. This preserves the historical accuracy of sent and accepted quotes.

### 4.2 Discount

Two modes, mutually exclusive per quote:

- **Percentage discount**: `discount_value` = e.g. 10 → `discount_amount` = `subtotal_gross × 0.10`
- **Fixed discount**: `discount_value` = e.g. 500 → `discount_amount` = 500 AZN

The discount is applied to the gross total (all sections combined), not per line item.

### 4.3 VAT

VAT is applied after discount: `vat_amount` = `subtotal_after_discount × (vat_rate / 100)`.

`vat_rate` is **company-specific** — each company configures its own rate in company settings (e.g. 18% for AZ domestic B2C). No percentage is hardcoded anywhere in the system. The VAT rate is copied onto the quote at creation time and can be overridden per quote (e.g. for VAT-exempt export contracts, set to 0).

### 4.4 Internal cost and profit (management-only)

```
section.subtotal_cost  = Σ item.line_total_cost   for all items in that section
total_internal_cost    = Σ section.subtotal_cost   for all sections in the quote
profit_before_vat      = subtotal_after_discount − total_internal_cost
profit_margin_pct      = profit_before_vat / subtotal_after_discount × 100
```

The internal view in the quote builder shows a per-section cost/profit breakdown (what this section costs us vs. what we're charging), plus the quote-level summary. These figures are **never** included in the customer-facing PDF.

The PDF shows section sale subtotals but no cost or profit information at any level.

---

## 5. PDF Layout

The PDF is the primary deliverable — it is what the customer sees, signs, and keeps. It must look professional, company-branded, and unambiguous.

### 5.1 Page structure (A4 portrait)

Each named section from the quote becomes a headed block in the PDF. Sections appear in the same order as in the quote builder. The logistics section ("Delivery & Logistics") is always last before the totals block.

```
┌─────────────────────────────────────────────────────┐
│  [Company Logo]              [Company Name]          │
│                              [Address, Phone, Email] │
│                              [Tax ID / VAT number]   │
├─────────────────────────────────────────────────────┤
│  QUOTATION                   Quote No: QT-2026-0042  │
│                              Version: v1             │
│                              Date: 01 July 2026      │
│                              Valid until: 31 July 2026│
├───────────────────┬─────────────────────────────────┤
│  PREPARED FOR     │  PROJECT                         │
│  Mirəli Həsənov   │  Villa Bağça                     │
│  +994 50 123 4567 │  Type: Residential               │
│  m@example.com    │  Address: Neftçilər pr. 12, Bakı  │
├───────────────────┴─────────────────────────────────┤
│                                                      │
│  ── KITCHEN ─────────────────────────────────────── │
│  ┌──────────────────────┬──────┬──────┬───────────┐  │
│  │ Description          │  Qty │ Unit │     Total │  │
│  ├──────────────────────┼──────┼──────┼───────────┤  │
│  │ NEOLITH Calacatta    │ 8.40 │  m²  │ 1,512 AZN │  │
│  │ Gold, 12mm, Polished │      │      │           │  │
│  │ Edge Profile – Eased │ 4.20 │  lm  │   105 AZN │  │
│  │ Sink Cutout ×1       │    1 │  pcs │    80 AZN │  │
│  │ Faucet Holes ×3      │    3 │  pcs │    45 AZN │  │
│  │ Cooktop Cutout ×1    │    1 │  pcs │    60 AZN │  │
│  │ Installation         │ 8.40 │  m²  │   336 AZN │  │
│  └──────────────────────┴──────┴──────┴───────────┘  │
│                       Section subtotal:  2,138 AZN   │
│                                                      │
│  ── ISLAND ──────────────────────────────────────── │
│  ┌──────────────────────┬──────┬──────┬───────────┐  │
│  │ NEOLITH Calacatta    │ 2.10 │  m²  │   378 AZN │  │
│  │ Gold, 12mm, Polished │      │      │           │  │
│  │ Edge Profile –       │ 2.40 │  lm  │    60 AZN │  │
│  │ Mitered Waterfall    │      │      │           │  │
│  │ Installation         │ 2.10 │  m²  │    84 AZN │  │
│  └──────────────────────┴──────┴──────┴───────────┘  │
│                       Section subtotal:    522 AZN   │
│                                                      │
│  ── MASTER BATHROOM ─────────────────────────────── │
│  ┌──────────────────────┬──────┬──────┬───────────┐  │
│  │ Vanity Top – Empera- │ 1.20 │  m²  │   240 AZN │  │
│  │ dor Dark, Polished   │      │      │           │  │
│  │ Wall Cladding –      │ 6.00 │  m²  │   720 AZN │  │
│  │ Empera dor Dark      │      │      │           │  │
│  │ Faucet Holes ×2      │    2 │  pcs │    30 AZN │  │
│  │ Installation         │ 7.20 │  m²  │   288 AZN │  │
│  └──────────────────────┴──────┴──────┴───────────┘  │
│                       Section subtotal:  1,278 AZN   │
│                                                      │
│  ── DELIVERY & LOGISTICS ───────────────────────── │
│  ┌──────────────────────┬──────┬──────┬───────────┐  │
│  │ Transport            │    1 │  trip│   150 AZN │  │
│  └──────────────────────┴──────┴──────┴───────────┘  │
│                       Section subtotal:    150 AZN   │
│                                                      │
│                          Subtotal:      4,088 AZN    │
│                          Discount (5%):  -204 AZN    │
│                          After discount: 3,884 AZN   │
│                          VAT (18%):       699 AZN    │
│                          ────────────────────────    │
│                          TOTAL:         4,583 AZN    │
├─────────────────────────────────────────────────────┤
│  Notes:                                              │
│  Price valid for standard slab sizes. Oversized      │
│  slabs subject to surcharge.                         │
├─────────────────────────────────────────────────────┤
│  Prepared by: [Rep Name]    Signature: ___________   │
│  [Legal footer text — configurable per company]      │
└─────────────────────────────────────────────────────┘
```

### 5.2 PDF generation rules

- **Company branding**: logo, name, address, phone, email, VAT number pulled from company settings. Each of the three companies (G-STONE GALLERY, KORONA PREMIUM, NEOLITH BAKU) gets its own branded PDF.
- **Section hierarchy**: each named section renders as a bold header ("── KITCHEN ──") followed by an item table, followed by a right-aligned section subtotal. Sections appear in `sort_order` sequence. Empty sections (no items) are never rendered.
- **Section subtotal**: shown at the bottom-right of each section's table. Allows the customer to see the cost of each space independently.
- **Column layout per section**: Description | Qty | Unit | Unit Price | Total. Unit label (m², lm, pcs) shown per row, not in a shared column header, because a single section may mix m² and lm items.
- **Delivery & Logistics section**: always rendered last, before the totals block, if it has any items (transport or crane). If neither transport nor crane is on the quote, this section is omitted entirely.
- **Totals block**: right-aligned, bottom of the last section. Shows Subtotal, Discount (only if non-zero), After Discount (only if discount applied), VAT with the actual rate displayed (e.g. "VAT 18%:", only if rate > 0), and **TOTAL** in bold. The VAT rate comes from the quote record — no hardcoded value.
- **Internal fields hidden**: cost prices, profit, internal notes, slab numbers — none of these appear anywhere on the customer PDF.
- **Quote number** on every page header (for multi-page quotes).
- **"Page N of M"** footer on every page.
- **Watermark "DRAFT"** printed diagonally across every page if the quote status is `draft`. Removed for all other statuses.
- **Language**: the PDF is rendered in the customer's preferred language (stored on the Customer record: az / ru / en). If the customer has no preferred language set, the language of the rep who is generating the PDF (their active UI locale) is used as fallback. Section headings, column headers, footer text, and the VAT label are all rendered in the resolved language.
- **File name**: `QT-2026-0042-v1_CustomerName.pdf`

### 5.3 Multi-page handling

If a quote has many line items, sections flow naturally onto page 2+. The totals block always starts on a new page if it would otherwise be split across a page break.

---

## 6. Quote Number Format

```
QT-{YYYY}-{NNNN}-v{V}
```

- `QT` — fixed prefix
- `YYYY` — calendar year of creation
- `NNNN` — zero-padded 4-digit sequential counter, **per company**, resetting each year
- `v{V}` — version number within the project (v1, v2, …)

Examples: `QT-2026-0001-v1`, `QT-2026-0001-v2`, `QT-2026-0042-v1`

The sequential counter is company-scoped (G-STONE GALLERY has its own sequence, KORONA PREMIUM has its own). It is generated atomically at quote creation time (no gaps in the sequence).

---

## 7. Permissions (RBAC)

| Action | Owner | Manager | Rep | Viewer |
|---|---|---|---|---|
| Create project | ✓ | ✓ | ✓ | — |
| View project | ✓ | ✓ | own | ✓ |
| Create quote | ✓ | ✓ | ✓ | — |
| View quote (incl. cost/profit) | ✓ | ✓ | — | — |
| View quote (sale prices only) | ✓ | ✓ | ✓ | ✓ |
| Edit draft quote | ✓ | ✓ | own | — |
| Mark as sent | ✓ | ✓ | own | — |
| Accept / decline quote | ✓ | ✓ | — | — |
| Generate PDF | ✓ | ✓ | ✓ | ✓ |
| Delete draft quote | ✓ | ✓ | — | — |

"own" = only quotes/projects assigned to that rep.

---

## 8. Events Published

| Event | Payload | Subscribers |
|---|---|---|
| `ProjectCreated` | project_id, company_id, customer_id | audit log |
| `QuoteCreated` | quote_id, project_id, customer_id, version | audit log |
| `QuoteStatusChanged` | quote_id, old_status, new_status | CRM (updates customer pipeline stage), audit log |
| `QuoteVersionCreated` | quote_id, project_id, version, parent_version | audit log — fires when auto-versioning creates a new draft from a sent quote |
| `QuoteAccepted` | quote_id, total_final, currency | Orders module (future) — triggers order creation |
| `SlabReserved` | slab_id, quote_id | Catalog (slab status → reserved; fires on QuoteAccepted) |
| `SlabReleased` | slab_id, quote_id | Catalog (slab status → available; fires on QuoteRejected / QuoteExpired) |

---

## 9. UI Screens

### 9.1 Projects list (`/sales/projects`)

Projects are a **first-class top-level module** — not hidden inside the Customer page. The top navigation gains a "Projects" entry pointing to `/sales/projects`.

Projects are also surfaced as a "Projects" tab on the Customer profile page (a filtered view of `/sales/projects?customer_id=X`) for reps navigating from a customer record. But the canonical home for Projects is the top-level route.

A Project is the central hub for everything that happens on a job: Quotes, Orders, Measurements, Production, Installation, Payments, Documents, and Photos. Future modules attach themselves to the Project rather than to the Customer directly.

Columns: Project Name, Type, Customer, Active Quote, Quote Total, Status, Assigned Rep, Created.
Actions: New Project, open project detail.

### 9.2 Project detail (`/sales/projects/[id]`)

- Project header (name, type, address, notes, customer link, assigned rep)
- Quote history table (version, status, total, date, actions: View, PDF, New Revision)
- "New Quote" button (creates v1 if first, or next version if existing)

### 9.3 Quote builder (`/sales/quotes/[id]`)

The main working screen. Split layout:

**Left panel — section + item editor:**

The left panel is a vertical list of collapsible section cards. Each card = one named section.

- **Add Section** button at the bottom creates a new blank section (prompts for a name).
- Sections can be reordered (drag handle or up/down arrows).
- Each section card shows:
  - Section name (editable inline)
  - An item table: rows for each item in the section
  - **Add item** row with a type selector (quick-add chips for the most common types: Material, Edge Profile, Sink Cutout, Faucet Holes, Cooktop Cutout, Installation; "Other" for anything else)
  - Section subtotal (sale price) on the bottom-right of the card
  - Expand/collapse toggle (collapsed shows only name + subtotal)

**Within a section card — two sub-panels:**

**(A) Measurements sub-panel** (collapsible; shown above items)

A table of measurement rows. Each row:
- Label (optional, e.g. "Countertop", "Window Sill")
- Length (mm) | Width (mm) | Thickness (mm, informational)
- Quantity (pieces)
- Area m² (computed live: L × W × Qty / 1 000 000, read-only)
- Waste % (pre-filled from company default, editable)
- Required area m² (computed live, **editable** — editing locks the field and sets `override_required_area = true`; a reset icon restores auto-calculation)
- Notes
- Delete row

Below the rows: **Section total measured area** = Σ required_area_m2 (shown prominently, e.g. "Total required: 8.40 m²"). This is a reference figure the rep can copy into the qty of a material item.

"Add measurement row" button adds a blank row.

**(B) Items sub-panel** (the pricing table)

- `material` / `wall_cladding` / `vanity` / `backsplash` items: material picker (search Catalog by name/brand/type), optional slab picker (filtered to this material + `available`), auto-fills unit prices from the quote's price list; qty field (m²); a "use measured area" button copies `section.total_measured_area` into the qty field as a convenience
- Service items (edge profile, cutouts, holes, installation): description field (pre-filled from item type, editable) + unit + qty; price auto-filled from company defaults, editable
- Each row: qty, unit, unit price, line total (computed), delete button

**Delivery & Logistics (pinned last section):**
- Transport and Crane as one-click toggles; adds a row to the logistics section with company default price; removing the row removes them

**Right panel — live summary:**
- Per-section subtotal breakdown (collapsible list)
- Quote-level subtotal gross
- Discount controls (none / % / fixed)
- VAT rate field (pre-filled from company default)
- Final total (large, prominent)
- Cost/profit summary (owner/manager only, hidden for reps)
- Action buttons: Save Draft | Preview PDF | Mark as Sent | Set to Negotiation | Accept | Reject

### 9.4 Quote view (read-only) (`/sales/quotes/[id]/view`)

For reps who can see sale prices but not cost: read-only layout matching the PDF, minus internal fields. "Download PDF" button.

### 9.5 Sales dashboard (`/sales`)

- Total quotes in pipeline (by status)
- Revenue this month (accepted quotes)
- Top materials quoted (by m² and by value)
- Quotes expiring this week

---

## 10. Database Tables Summary

| Table | Purpose |
|---|---|
| `sales_projects` | One job per customer; first-class business object; future hub for Orders, Production, Installation, Payments, Documents, Photos |
| `sales_quotes` | Quote header (one row per version; immutable once sent); holds discount, VAT, and all aggregated totals |
| `sales_quote_sections` | Named sections within a quote (Kitchen, Island, Master Bathroom, etc.); holds sale/cost subtotals and the aggregated total_measured_area |
| `sales_quote_section_measurements` | Measurement rows within a section (one row per distinct piece/group); stores L/W/thickness/qty, computed area, waste %, required area, override flag; reused by Production and Installation modules |
| `sales_quote_section_items` | Pricing line items within a section (material, edge_profile, sink_cutout, etc.); holds quantity, unit, sale price, cost price, and computed line totals |
| `sales_quote_number_seq` | Atomic per-company-per-year counter for quote numbers |
| `company_service_prices` | Per-company default prices for work/logistics item types (transport, installation, crane, sink cutout, etc.); managed by Owners at `/settings/service-prices` |

All tables: `company_id` (multi-tenancy), `created_at`, `updated_at`. Foreign keys to `crm_customers` and `catalog_materials` / `catalog_slabs`.

---

## 11. Out of Scope (this module)

- **Order creation**: `QuoteAccepted` is published; the Orders module (next) subscribes and creates the Order. The Quotes module does not create Orders itself.
- **Payment terms / invoicing**: Finance module (later).
- **Digital signature**: outside scope for now; the PDF is printed and signed manually.
- **Customer portal / self-serve**: out of scope; the PDF is delivered by the rep (email, WhatsApp).
- **Configurable price lists for work items** (edge profiles, cutouts): in v1, these are manually typed or remembered by rep. A future version may add a "Work Price List" entity so standard work prices are pulled automatically.
- **Multi-currency per line item**: all lines on a quote share one currency. Cross-currency quoting is out of scope.

---

## 12. Architectural Decisions (approved 2026-07-01)

All of the following were raised as open questions and have been resolved:

1. **Project navigation**: top-level `/sales/projects` module — Projects are first-class business objects, not subordinate to Customer. Also surfaced as a filtered tab on the Customer profile for contextual navigation. ✅

2. **Work item default prices**: stored per company in `company_settings` as `default_service_prices` — a keyed map editable by Owners at `/settings/service-prices`. Covers transport, installation (per m² and flat), crane, sink cutout, cooktop cutout, faucet hole, edge profile (per lm). Reps may override per line item. ✅

3. **VAT**: entirely company-specific; no percentage hardcoded anywhere. Each company configures its own default VAT rate. Copied onto the quote at creation; editable per quote for exceptions. ✅

4. **PDF language**: customer's `preferred_language` field first; falls back to the generating rep's active UI locale. ✅

5. **Slab reservation**: reserved **only on `accepted`** — not on draft, sent, or negotiation. Released automatically on `rejected` or `expired`. Concurrent acceptance conflict handled with an explicit error. ✅

6. **Quote versioning**: quotes in `draft` status are freely editable. Any mutation of a `sent`, `negotiation`, or `accepted` quote automatically creates a new `draft` version — the prior sent version is never overwritten. ✅

7. **Quote Sections (approved 2026-07-01)**: a quote is not a flat line-item list. It is a hierarchy of named sections (Kitchen, Island, Bathroom, Staircase, Outdoor, etc.) each containing typed items. Sections mirror the physical spaces on the job site. The PDF preserves this hierarchy — each section renders as a headed block with its own subtotal. The quote header aggregates all section subtotals. The flat `section` enum on line items is replaced by the two-table model: `sales_quote_sections` (named, ordered, with subtotals) + `sales_quote_section_items` (typed items within a section). ✅

8. **Section Measurements (approved 2026-07-01)**: each section optionally holds one or more measurement rows (`sales_quote_section_measurements`). Each row stores: label, length_mm, width_mm, thickness_mm, quantity, computed `area_m2` (L × W × Qty / 1 000 000), `waste_pct`, computed `required_area_m2` (area + waste), and an override flag so the rep can lock the required area to a custom value. The section aggregates all rows into `total_measured_area`. Measurements are a reference for material pricing — the rep uses "use measured area" to copy the total into a material item's qty, but the system does not force it. The `sales_quote_section_measurements` table is read directly by the Production and Installation modules; they never re-enter dimensions. Default waste % is configurable per company. ✅

---

**This design is FROZEN as of 2026-07-01. Implementation may begin.**

---

## 13. Dependency Checklist

Before implementation begins, the following must be confirmed available:

- [x] CRM `customers` table (UUID PK, company_id)
- [x] Catalog `materials` table (UUID PK, company_id, name, material_type)
- [x] Catalog `slabs` table (UUID PK, company_id, material_id, status, area_m2)
- [x] Catalog `price_list_entries` table (price_list_id, material_id, sale_price, cost_price)
- [x] Core `users` table (for assigned_to / prepared_by)
- [x] Core event bus (`event_bus.publish`)
- [x] Core audit service (`record_audit`)
- [x] Core document storage (for PDF storage — or generated on-demand; TBD at implementation)
- [ ] PDF generation library (WeasyPrint or ReportLab — to be chosen at implementation)

All checked items are already live in the codebase as of commit `c1e7dc6`.
