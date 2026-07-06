# G-ERP — Database Design

_Date: 2026-06-29_
_Status: Phase 1 design document. Derived from the frozen [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) architecture (single PostgreSQL/Supabase database, company-scoped Row-Level Security, plugin modules each owning their own tables/migrations)._

This document covers the database for **Foundation + CRM + Sales** in full detail (the modules built in Phase 1), and gives the conceptual schema for later modules (Inventory, Purchasing, Production, Installation, Finance, Reports, Marketing, AI) so the ER design is coherent end-to-end. Tables for later-phase modules will get their own Alembic migrations when each module's phase begins — they are not built now.

---

## 1. Conventions

- All primary keys: `id` UUID (`gen_random_uuid()` / `uuidv7` candidate — decide at Phase 1 migration-writing time), not auto-increment integers, to avoid cross-company ID-guessing and to support future offline mobile sync.
- All tenant-owned tables include `company_id UUID NOT NULL REFERENCES companies(id)`.
- All tables include `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`; mutable tables also include `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (maintained via trigger or ORM hook).
- Soft delete via `deleted_at TIMESTAMPTZ NULL` on user-facing records (contacts, accounts, deals, etc.) rather than hard delete, to preserve audit/history integrity. Core/system tables (audit_log, event_log) are append-only and never deleted.
- Foreign keys default to `ON DELETE RESTRICT` unless explicitly noted, to prevent accidental cascading data loss across modules.
- Every `company_id` column is indexed; every table expected to be filtered/joined by another foreign key in normal queries gets a composite index covering `(company_id, <that_column>)`.
- Money columns: `NUMERIC(14,2)` plus a `currency CHAR(3)` column where currency can vary; AZN is the default.

## 2. Entity-Relationship Diagram (Phase 1 scope: Core + CRM + Sales)

```
companies ──┬───────────────< user_company_roles >───────────────── users
            │
            ├──< contacts
            ├──< accounts ──< account_contacts >── contacts
            ├──< leads ── (converts to) ──> deals
            ├──< pipeline_stages ──< deals
            ├──< deals >──┬── account_id ──> accounts
            │             ├── contact_id ──> contacts
            │             ├── stage_id ────> pipeline_stages
            │             └── owner_user_id ─> users
            ├──< activities >── related_entity (contact | account | deal)
            ├──< tasks >──── related_entity (contact | account | deal)
            ├──< quotes >──── account_id ──> accounts, deal_id ──> deals
            ├──< quote_lines >── quote_id ──> quotes
            ├──< sales_orders >── quote_id ──> quotes, account_id ──> accounts
            ├──< sales_order_lines >── sales_order_id ──> sales_orders
            ├──< documents >── related_entity (any module's entity)
            ├──< audit_log >── actor_user_id ──> users
            └──< event_log >── company_id (mandatory on every event)
```

Conceptual extension (future phases, shown for schema coherence — not built in Phase 1):

```
sales_orders ──< work_orders (Production) ──< stock_movements (Inventory)
sales_orders ──< installation_jobs (Installation)
sales_orders / installation_jobs ──< invoices (Finance) ──< payments (Finance)
suppliers (Purchasing) ──< purchase_orders ──< purchase_order_lines ──> stock_items (Inventory)
campaigns (Marketing) ──< leads
ai_jobs (Core, consumed by AI module) ── related_entity (any)
```

## 3. Core Tables (own no module — shared platform tables, per the plugin architecture's "companies is part of the core contract" rule)

### 3.1 `companies`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | TEXT | NOT NULL |
| slug | TEXT | NOT NULL, UNIQUE |
| currency | CHAR(3) | NOT NULL, DEFAULT 'AZN' |
| locale | TEXT | NOT NULL, DEFAULT 'en' |
| logo_url | TEXT | NULL |
| enabled_modules | JSONB | NOT NULL, DEFAULT '[]' — list of module names enabled for this company |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

Seed rows at Phase 1: G-STONE GALLERY, KORONA PREMIUM, NEOLITH BAKU.

### 3.2 `users`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL |
| full_name | TEXT | NOT NULL |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

### 3.3 `user_company_roles`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE |
| company_id | UUID | NOT NULL, REFERENCES companies(id) ON DELETE CASCADE |
| role | TEXT | NOT NULL, CHECK IN ('owner','manager','rep','viewer') |
| module_permissions | JSONB | NOT NULL, DEFAULT '{}' — per-module role override |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Constraints**: UNIQUE (`user_id`, `company_id`) — one role record per user per company.
**Indexes**: (`user_id`), (`company_id`).

### 3.4 `documents`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| module | TEXT | NOT NULL — which module's entity this is attached to |
| related_entity_type | TEXT | NOT NULL |
| related_entity_id | UUID | NOT NULL |
| storage_path | TEXT | NOT NULL — Supabase Storage key |
| mime_type | TEXT | NOT NULL |
| uploaded_by | UUID | NOT NULL, REFERENCES users(id) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`), (`related_entity_type`, `related_entity_id`).

### 3.5 `audit_log`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| module | TEXT | NOT NULL |
| actor_user_id | UUID | NOT NULL, REFERENCES users(id) |
| action | TEXT | NOT NULL |
| entity_type | TEXT | NOT NULL |
| entity_id | UUID | NOT NULL |
| diff_json | JSONB | NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`, `created_at`), (`entity_type`, `entity_id`). Append-only — no UPDATE/DELETE permitted at the application layer.

### 3.6 `event_log`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| event_name | TEXT | NOT NULL |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| payload | JSONB | NOT NULL |
| published_by_module | TEXT | NOT NULL |
| processed_by | JSONB | NOT NULL, DEFAULT '[]' — list of subscriber modules that have handled it |
| occurred_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`, `occurred_at`), (`event_name`). Append-only.

### 3.7 `ai_jobs` (table reserved now, populated starting in the AI module's phase)
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| module | TEXT | NOT NULL |
| job_type | TEXT | NOT NULL, CHECK IN ('ocr','vision','nlp','ml') |
| status | TEXT | NOT NULL, CHECK IN ('queued','running','completed','failed') |
| input_ref | TEXT | NULL — reference to a `documents.id` or other source |
| result_json | JSONB | NULL |
| celery_task_id | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| completed_at | TIMESTAMPTZ | NULL |

**Indexes**: (`company_id`, `status`).

## 4. CRM Module Tables

### 4.1 `contacts`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| full_name | TEXT | NOT NULL |
| email | TEXT | NULL |
| phone | TEXT | NULL |
| source | TEXT | NULL |
| tags | TEXT[] | NOT NULL, DEFAULT '{}' |
| created_by | UUID | NOT NULL, REFERENCES users(id) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| deleted_at | TIMESTAMPTZ | NULL |

**Indexes**: (`company_id`), (`company_id`, `email`), GIN index on `tags`.
**Constraints**: at least one of `email`/`phone` NOT NULL (checked at application layer; DB-level `CHECK (email IS NOT NULL OR phone IS NOT NULL)` also applied).

### 4.2 `accounts`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| name | TEXT | NOT NULL |
| type | TEXT | NOT NULL, CHECK IN ('individual','business') |
| primary_contact_id | UUID | NULL, REFERENCES contacts(id) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| deleted_at | TIMESTAMPTZ | NULL |

**Indexes**: (`company_id`), (`company_id`, `name`).

### 4.3 `account_contacts` (many-to-many: an account may have multiple associated contacts)
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| account_id | UUID | NOT NULL, REFERENCES accounts(id) ON DELETE CASCADE |
| contact_id | UUID | NOT NULL, REFERENCES contacts(id) ON DELETE CASCADE |
| relationship | TEXT | NULL (e.g., "billing contact") |

**Constraints**: UNIQUE (`account_id`, `contact_id`).

### 4.4 `leads`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| full_name | TEXT | NOT NULL |
| email | TEXT | NULL |
| phone | TEXT | NULL |
| source | TEXT | NULL — links conceptually to Marketing's `lead_sources` in a later phase |
| status | TEXT | NOT NULL, CHECK IN ('new','contacted','qualified','converted','disqualified'), DEFAULT 'new' |
| converted_contact_id | UUID | NULL, REFERENCES contacts(id) |
| converted_deal_id | UUID | NULL, REFERENCES deals(id) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`, `status`).

### 4.5 `pipeline_stages`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| name | TEXT | NOT NULL |
| order_index | INTEGER | NOT NULL |
| is_won | BOOLEAN | NOT NULL, DEFAULT false |
| is_lost | BOOLEAN | NOT NULL, DEFAULT false |

**Constraints**: UNIQUE (`company_id`, `order_index`). Per-company configurable, per revision 2's "configurable pipeline" requirement.
**Indexes**: (`company_id`).

### 4.6 `deals`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| account_id | UUID | NOT NULL, REFERENCES accounts(id) |
| contact_id | UUID | NULL, REFERENCES contacts(id) |
| stage_id | UUID | NOT NULL, REFERENCES pipeline_stages(id) |
| title | TEXT | NOT NULL |
| value | NUMERIC(14,2) | NOT NULL, DEFAULT 0 |
| currency | CHAR(3) | NOT NULL, DEFAULT 'AZN' |
| expected_close_date | DATE | NULL |
| owner_user_id | UUID | NOT NULL, REFERENCES users(id) |
| status | TEXT | NOT NULL, CHECK IN ('open','won','lost'), DEFAULT 'open' |
| lost_reason | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| deleted_at | TIMESTAMPTZ | NULL |

**Indexes**: (`company_id`, `stage_id`), (`company_id`, `owner_user_id`), (`company_id`, `status`).
**Constraint**: `CHECK (value >= 0)`.

### 4.7 `activities`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| type | TEXT | NOT NULL, CHECK IN ('note','call','email','meeting') |
| body | TEXT | NOT NULL |
| related_entity_type | TEXT | NOT NULL, CHECK IN ('contact','account','deal') |
| related_entity_id | UUID | NOT NULL |
| created_by | UUID | NOT NULL, REFERENCES users(id) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`, `related_entity_type`, `related_entity_id`).
Polymorphic relation is enforced at the application layer (no DB-level FK across the polymorphic boundary); integrity tests in CI assert orphan-free data.

### 4.8 `tasks`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| title | TEXT | NOT NULL |
| due_date | TIMESTAMPTZ | NULL |
| assigned_to | UUID | NOT NULL, REFERENCES users(id) |
| related_entity_type | TEXT | NULL, CHECK IN ('contact','account','deal') |
| related_entity_id | UUID | NULL |
| status | TEXT | NOT NULL, CHECK IN ('open','done','cancelled'), DEFAULT 'open' |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`, `assigned_to`, `status`), (`company_id`, `due_date`).

## 5. Sales Module Tables

### 5.1 `quotes`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| account_id | UUID | NOT NULL, REFERENCES accounts(id) |
| deal_id | UUID | NULL, REFERENCES deals(id) |
| status | TEXT | NOT NULL, CHECK IN ('draft','sent','accepted','rejected','expired'), DEFAULT 'draft' |
| total_amount | NUMERIC(14,2) | NOT NULL, DEFAULT 0 |
| currency | CHAR(3) | NOT NULL, DEFAULT 'AZN' |
| valid_until | DATE | NULL |
| created_by | UUID | NOT NULL, REFERENCES users(id) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`, `status`), (`account_id`).

### 5.2 `quote_lines`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| quote_id | UUID | NOT NULL, REFERENCES quotes(id) ON DELETE CASCADE |
| description | TEXT | NOT NULL |
| quantity | NUMERIC(12,2) | NOT NULL, CHECK (quantity > 0) |
| unit_price | NUMERIC(14,2) | NOT NULL, CHECK (unit_price >= 0) |
| line_total | NUMERIC(14,2) | NOT NULL, GENERATED ALWAYS AS (quantity * unit_price) STORED |

**Indexes**: (`quote_id`).

### 5.3 `sales_orders`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id) |
| quote_id | UUID | NULL, REFERENCES quotes(id) |
| account_id | UUID | NOT NULL, REFERENCES accounts(id) |
| status | TEXT | NOT NULL, CHECK IN ('pending_approval','approved','in_progress','completed','cancelled'), DEFAULT 'pending_approval' |
| total_amount | NUMERIC(14,2) | NOT NULL, DEFAULT 0 |
| currency | CHAR(3) | NOT NULL, DEFAULT 'AZN' |
| approved_by | UUID | NULL, REFERENCES users(id) |
| approved_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

**Indexes**: (`company_id`, `status`), (`account_id`).
Approval (status → `approved`) is what publishes the `OrderApproved` domain event (per the frozen architecture's EDA design) — this table does not reference Production/Inventory directly; those modules subscribe to the event instead.

### 5.4 `sales_order_lines`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| sales_order_id | UUID | NOT NULL, REFERENCES sales_orders(id) ON DELETE CASCADE |
| description | TEXT | NOT NULL |
| quantity | NUMERIC(12,2) | NOT NULL, CHECK (quantity > 0) |
| unit_price | NUMERIC(14,2) | NOT NULL, CHECK (unit_price >= 0) |
| line_total | NUMERIC(14,2) | NOT NULL, GENERATED ALWAYS AS (quantity * unit_price) STORED |

**Indexes**: (`sales_order_id`).

## 5.5 Stone Catalog Module Tables (Version 2.0 — as actually implemented)

_Note: built ahead of the Sales module per [ROADMAP.md](ROADMAP.md)'s revised dependency chain (quotations need real stone data to quote from). Table names are prefixed `catalog_` rather than left bare, matching the convention actually used by the implemented CRM module (`crm_*`) rather than the unprefixed names sketched in section 4 above._

### 5.5.1 `catalog_brands`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| name | TEXT | NOT NULL |
| description | TEXT | nullable |
| logo_document_id | UUID | nullable, REFERENCES documents(id) |
| status | TEXT | NOT NULL, default `active` (`active`\|`hidden`), indexed |
| created_by | UUID | REFERENCES users(id) |

### 5.5.2 `catalog_collections`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| brand_id | UUID | NOT NULL, REFERENCES catalog_brands(id), indexed |
| name | TEXT | NOT NULL |
| description | TEXT | nullable |
| status | TEXT | NOT NULL, default `active`, indexed |

### 5.5.3 `catalog_materials` (the sellable design/SKU)
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| brand_id | UUID | NOT NULL, REFERENCES catalog_brands(id), indexed |
| collection_id | UUID | nullable, REFERENCES catalog_collections(id), indexed |
| name | TEXT | NOT NULL |
| material_type | TEXT | nullable (e.g. Sintered Stone, Porcelain, Quartz, Natural Marble, Natural Granite, Dekton, Ceramic) |
| color, finish, thickness_mm, dimensions, country_of_origin | TEXT | nullable |
| description | TEXT | nullable |
| status | TEXT | NOT NULL, default `active` (`active`\|`hidden`), indexed |

### 5.5.4 `catalog_warehouses`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| name | TEXT | NOT NULL |
| address | TEXT | nullable |
| status | TEXT | NOT NULL, default `active`, indexed |

### 5.5.5 `catalog_slabs` (individually tracked physical inventory)
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| material_id | UUID | NOT NULL, REFERENCES catalog_materials(id), indexed |
| warehouse_id | UUID | NOT NULL, REFERENCES catalog_warehouses(id), indexed |
| slab_number | TEXT | NOT NULL, indexed, UNIQUE per `(company_id, slab_number)` |
| lot_number, barcode | TEXT | nullable, indexed |
| rack_location | TEXT | nullable |
| length_mm, width_mm | NUMERIC(10,2) | nullable |
| area_m2 | NUMERIC(10,3) | nullable — computed in the application layer as `length_mm * width_mm / 1_000_000` at create time, not a DB-generated column (keeps SQLite/Postgres portability) |
| weight_kg | NUMERIC(10,2) | nullable |
| status | TEXT | NOT NULL, default `available`, indexed. One of `available`\|`reserved`\|`sold`\|`in_production`\|`scrap`, enforced by a domain-layer transition graph (`sold` and `scrap` are terminal; `scrap` reachable from any non-terminal state) — not a free-form enum |

### 5.5.6 `catalog_price_lists` / `catalog_price_list_entries`
Company-specific pricing is modeled as a named header (`catalog_price_lists`: `name`, `currency` default `AZN`, `is_default`, `status`) with per-material line items (`catalog_price_list_entries`: `price_list_id`, `material_id`, `cost_price` NUMERIC(14,2), `sale_price` NUMERIC(14,2), `UNIQUE(price_list_id, material_id)`) — allowing multiple price lists per company (e.g. retail vs. wholesale) rather than a single price column bolted onto `catalog_materials`.

### 5.5.7 `catalog_material_images` / `catalog_material_documents`
Thin join tables linking a `catalog_materials` row to a core `documents` row (the same shared upload/storage pipeline CRM attachments use — no separate file-handling code). `catalog_material_images.image_type` is one of `gallery`\|`thumbnail`\|`bookmatch_left`\|`bookmatch_right`; `catalog_material_documents.document_type` is one of `technical_pdf`\|`installation_guide`\|`cleaning_guide`.

## 5.6 Communication Center Module Tables (Version 2.7 — as actually implemented)

_Note: a unified omnichannel inbox (WhatsApp Business, Instagram Direct, Facebook Messenger, Email, SMS) integrated with CRM. No real WhatsApp/Instagram/Messenger/email/SMS provider is wired up yet, by explicit design — see `modules/communication/infrastructure/providers/` for the provider abstraction every real integration will later implement without any schema or endpoint change._

### 5.6.1 `communication_channels`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| channel_type | TEXT | NOT NULL, indexed. One of `whatsapp`\|`instagram`\|`messenger`\|`email`\|`sms` |
| display_name | TEXT | NOT NULL |
| identifier | TEXT | nullable — the channel's own address (phone number, email address, ...) |
| is_active | BOOLEAN | NOT NULL, default `true` |
| created_by | UUID | nullable, REFERENCES users(id) |

A company may have several rows of the same `channel_type` (e.g. multiple WhatsApp Business numbers) — there is no one-per-type uniqueness constraint.

### 5.6.2 `communication_conversations`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| channel_id | UUID | NOT NULL, REFERENCES communication_channels(id), indexed |
| customer_id | UUID | nullable, REFERENCES crm_customers(id), indexed |
| lead_id | UUID | nullable, REFERENCES crm_leads(id), indexed |
| project_id | UUID | nullable, REFERENCES sales_projects(id), indexed |
| quote_id | UUID | nullable, REFERENCES sales_quotes(id), indexed |
| order_id | UUID | nullable, REFERENCES orders(id), indexed |
| external_contact_id | TEXT | NOT NULL, indexed — the counterpart's address on the channel (phone/handle/PSID/email) |
| external_contact_name | TEXT | nullable |
| status | TEXT | NOT NULL, default `open` (`open`\|`pending`\|`closed`), indexed — freely reachable from one another, no terminal state |
| assigned_to | UUID | nullable, REFERENCES users(id), indexed |
| tags | JSON | NOT NULL, default `[]` |
| unread_count | INTEGER | NOT NULL, default `0` |
| last_message_at | TIMESTAMPTZ | nullable, indexed |
| last_message_preview | TEXT(300) | nullable |
| created_by | UUID | nullable, REFERENCES users(id) |

One conversation per `(company_id, channel_id, external_contact_id)` — a returning sender's messages all land in the same thread. `customer_id`/`lead_id` are populated by `GetOrCreateConversationUseCase`: it matches the sender against an existing CRM Customer using the field the channel naturally maps onto (`whatsapp`→`Customer.whatsapp`, `instagram`→`Customer.instagram`, `messenger`→`Customer.facebook`, `email`→`Customer.email`, `sms`→`Customer.phone`), and **auto-creates a Lead** (reusing CRM's own `CreateLeadUseCase`) if no match is found.

### 5.6.3 `communication_messages`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| conversation_id | UUID | NOT NULL, REFERENCES communication_conversations(id), indexed |
| direction | TEXT | NOT NULL, indexed (`inbound`\|`outbound`) |
| sender_type | TEXT | NOT NULL (`customer`\|`agent`\|`system`) |
| sender_user_id | UUID | nullable, REFERENCES users(id) — set for outbound agent messages |
| message_type | TEXT | NOT NULL, default `text` (`text`\|`image`\|`document`\|`audio`\|`video`\|`template`) |
| body | TEXT | nullable |
| template_id | UUID | nullable, REFERENCES communication_message_templates(id) |
| external_message_id | TEXT | nullable — the provider-assigned id (a local placeholder id today; see 5.6 note above) |
| status | TEXT | NOT NULL, default `sent` (`received`\|`sent`\|`delivered`\|`read`\|`failed`) |

### 5.6.4 `communication_message_attachments`
Thin join table linking a `communication_messages` row to a core `documents` row — the same shared upload/storage pipeline CRM attachments and Catalog material images use. Columns: `message_id`, `document_id`, `file_name` (nullable).

### 5.6.5 `communication_conversation_notes`
Internal, customer-invisible notes on a conversation: `conversation_id`, `body` (TEXT, NOT NULL), `created_by`.

### 5.6.6 `communication_message_templates`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| name | TEXT | NOT NULL |
| channel_type | TEXT | nullable, indexed — `null` means usable on any channel |
| shortcut | TEXT | nullable, indexed — a quick-reply trigger (e.g. `thanks`) |
| body | TEXT | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default `true` |
| created_by | UUID | nullable |

Covers both "message templates" and "quick replies" as one entity distinguished only by whether `shortcut` is set, rather than two near-identical tables.

## 5.7 AI Sales Assistant Module Tables (Version 2.8 — as actually implemented)

_Note: provider-agnostic AI recommendations layered on CRM, Communication, Sales, and Tasks. No real LLM provider is wired up yet, by explicit design — every provider name resolves to `MockAIProvider`, a deterministic heuristic engine, so the rest of the platform can be built and tested against a stable contract; see `modules/ai/infrastructure/providers/` for the abstraction a real provider will later implement without any schema or endpoint change._

### 5.7.1 `ai_recommendations`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| analysis_kind | TEXT | NOT NULL, indexed. One of `lead`\|`conversation`\|`quote`\|`task` — the analysis entry point that produced this row |
| recommendation_type | TEXT | NOT NULL, indexed. One of 27 values across CRM/Communication/Sales/Task Intelligence (e.g. `lead_score`, `conversation_sentiment`, `upsell_suggestion`, `overdue_risk`) |
| related_entity_type | TEXT | nullable, indexed — e.g. `lead`\|`customer`\|`conversation`\|`quote`\|`task` |
| related_entity_id | UUID | nullable, indexed |
| provider | TEXT | NOT NULL, default `mock`, indexed |
| model | TEXT | NOT NULL, default `""` |
| prompt | TEXT | NOT NULL — the exact prompt string sent to the provider |
| response | JSON | NOT NULL — the provider's full structured output |
| confidence_score | NUMERIC(4,3) | nullable — provider-reported, 0.000–1.000 |
| execution_time_ms | INTEGER | nullable — measured by the calling use case around the provider call, not self-reported, so it stays comparable across every future provider |
| summary | TEXT(500) | nullable — short human-readable one-liner for list/dashboard display |
| status | TEXT | NOT NULL, default `pending`, indexed (`pending`\|`accepted`\|`rejected`\|`edited`) |
| edited_response | JSON | nullable — the user-edited payload, set only when `status = edited` |
| requested_by | UUID | nullable, REFERENCES users(id) |
| reviewed_by | UUID | nullable, REFERENCES users(id) |
| reviewed_at | TIMESTAMPTZ | nullable |

One table covers all 27 recommendation types, discriminated by `recommendation_type`, rather than one table per type — the same pattern as `communication_message_templates` covering both templates and quick replies. **Nothing in this module ever writes to another module's tables** as a side effect of analysis or of a review decision — accepting/rejecting/editing a recommendation only ever updates this table's own `status`/`reviewed_by`/`reviewed_at`/`edited_response` columns, which is what makes "AI never performs business actions automatically" a structural property rather than a UI convention.

## 6. Future-Phase Module Schemas (conceptual — not migrated in Phase 1)

Kept here only so foreign-key shapes are pre-considered and won't surprise later modules.

- **Inventory**: `warehouses(id, company_id, name)`, `stock_items(id, company_id, sku, name, unit)`, `stock_lots(id, stock_item_id, lot_number, dimensions_json)`, `stock_movements(id, stock_item_id, warehouse_id, quantity, movement_type, related_entity_type, related_entity_id)`.
- **Purchasing**: `suppliers(id, company_id, name, contact_info)`, `purchase_orders(id, company_id, supplier_id, status)`, `purchase_order_lines(id, purchase_order_id, stock_item_id, quantity, unit_cost)`, `goods_receipts(id, purchase_order_id, received_at)`.
- **Production**: `work_orders(id, company_id, sales_order_id, status)`, `work_order_stages(id, work_order_id, name, status, order_index)`, `material_consumption(id, work_order_id, stock_item_id, quantity_consumed)`.
- **Installation**: `installation_jobs(id, company_id, sales_order_id, scheduled_at, status)`, `installation_crew_assignments(id, installation_job_id, user_id)`.
- **Finance**: `invoices(id, company_id, sales_order_id, installation_job_id, status, total_amount)`, `invoice_lines(id, invoice_id, description, amount)`, `payments(id, invoice_id, amount, paid_at, method)`, `expenses(id, company_id, related_entity_type, related_entity_id, amount)`.
- **Marketing**: `campaigns(id, company_id, name, channel, start_date, end_date)`, `lead_sources(id, company_id, campaign_id, name)`.
- **AI**: relies on core `ai_jobs`; module-specific result tables (e.g., `extracted_invoice_data`) added when that capability is built.

Each will get its own `infrastructure/migrations/` directory and Alembic revision chain when its phase begins, per the frozen plugin contract.

## 7. Row-Level Security Strategy

Every tenant-owned table gets an RLS policy of the shape:

```sql
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON contacts
  USING (company_id = current_setting('app.current_company_id')::uuid);
```

The backend sets `app.current_company_id` (via `SET LOCAL` at the start of each request's DB transaction, derived from the authenticated user's active company context — never from a client-supplied value) so RLS is a true defense-in-depth layer behind the application-level `company_id` filtering already present in every repository query.

## 8. Migration Strategy

- Alembic revision history is unified at the database level but each module owns its own migration scripts under its `infrastructure/migrations/` directory (per frozen architecture §4.4/5.2).
- Core platform tables (`companies`, `users`, `user_company_roles`, `documents`, `audit_log`, `event_log`, `ai_jobs`) are created in the Foundation phase's migration set, before any module migration runs.
- CI runs `alembic upgrade head` against a disposable test database on every PR before merge.
- Module removal does not auto-drop tables; a deliberate downgrade migration is required if data removal is intended.
