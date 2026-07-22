# G-ERP — Database Design

_Originally a Phase 1 design document (2026-06-29); rewritten 2026-07-21 against the actual current SQLAlchemy models (every `infrastructure/models/*.py` file in `backend/`, not the original design) to close `PROJECT_AUDIT.md` Priority #4 — the previous revision described a superseded Phase-1 CRM/Sales schema that was never actually built that way, and still listed Production/Installation/Finance as "conceptual, not migrated" long after all three shipped._
_Status: covers every table in every one of the thirteen installed modules, as implemented as of Version 2.33.0, verified directly against model source files and Alembic migrations._

---

## 1. Conventions

- All primary keys: `id UUID`, generated **application-side** via Python's `uuid.uuid4()` at the SQLAlchemy `default=` — not a Postgres-side `gen_random_uuid()`/`uuidv7()` function (that Phase-1 open question was resolved this way in practice, not documented until now). Stored via the `GUID` `TypeDecorator` (`core/db/mixins.py`) — native `UUID` on Postgres, `CHAR(36)` on SQLite, which is what lets the entire test suite run against in-memory SQLite while production runs Postgres/Supabase.
- All tenant-owned tables include `company_id UUID NOT NULL REFERENCES companies(id)`, hand-declared per model (not inherited from a mixin's mapped column, since declarative mapping needs a concrete FK target) and indexed in the overwhelming majority of cases.
- Every table includes `created_at`/`updated_at` (`TimestampMixin`) as `TIMESTAMPTZ NOT NULL`, defaulted via a Python `_utcnow()` callable at the ORM layer (not a DB `server_default`) — with two documented exceptions: `crm_activities` (has `created_at` only, via `server_default=func.now()`, no `updated_at`) and the four `*_number_sequence` tables (no timestamps at all, by design — they are pure atomic counters, not user-facing records).
- **No foreign key in any module declares `ondelete=` at the ORM level**, except `user_company_roles` (`ON DELETE CASCADE` on both `user_id` and `company_id` — the one deliberate exception, since a role record is meaningless without both). Every other FK across all ten modules defaults to the database's own default behavior (RESTRICT/NO ACTION), not an app-declared cascade — verified by grep across every model file. Soft delete via `deleted_at TIMESTAMPTZ NULL` is used on `crm_customers`/`crm_contacts`; most other business entities use a `status` value (e.g. `hidden`, `cancelled`) rather than a `deleted_at` column.
- Every `company_id` column is indexed. Composite indexes exist wherever a hot query filters by `company_id` plus one more column — e.g. `crm_customers`/`crm_leads`'s status/source composites (§4), added retroactively by migration `e042f8386f09` once the actual query patterns were known, not speculatively upfront.
- Money columns: `NUMERIC(14,2)` (occasionally `NUMERIC(5,2)` for percentages like VAT rate) plus a `currency TEXT(3)` column where currency can vary; `"AZN"` is the default everywhere.
- Several business-date columns (`scheduled_date`, `expense_date`, `valid_until`, etc.) are stored as plain `TEXT(10)` ISO date strings rather than a `DATE` column — a deliberate SQLite/Postgres portability choice made early and kept consistent since, not an inconsistency to "fix."
- Status/enum-like columns are plain `TEXT` with the valid-value set enforced in the domain layer (`domain/value_objects.py` per module, typically a `VALID_*` frozenset plus, for stateful entities, an explicit transition graph), not a DB-level `CHECK` constraint or native enum type — this is a real, consistent choice across every module, not a Phase-1-only shortcut.

## 2. Entity-Relationship Diagram (current, all thirteen installed modules)

```
companies ──┬──────< user_company_roles >────────────────── users
            │
            ├──< crm_customers ──< crm_contacts (circular: customers.primary_contact_id ⇄ contacts.customer_id)
            ├──< crm_leads ── (converts to) ──> crm_customers / crm_contacts
            ├──< crm_tasks (polymorphic related_entity_type/id; self-referential series_id)
            ├──< crm_task_notifications >── task_id ──> crm_tasks
            ├──< crm_activities (polymorphic related_entity_type/id)
            │
            ├──< catalog_brands ──< catalog_collections ──< catalog_materials
            ├──< catalog_materials ──< catalog_material_thicknesses / catalog_material_sizes
            ├──< catalog_materials ──< catalog_material_images / catalog_material_documents >── documents
            ├──< catalog_warehouses ──< catalog_slabs >── catalog_materials
            ├──< catalog_price_lists ──< catalog_price_list_entries >── catalog_materials
            │
            ├──< sales_projects ── customer_id ──> crm_customers
            ├──< sales_projects ──< sales_rooms ──< sales_project_items >── material_id/thickness_id/size_id ──> catalog_materials/*
            ├──< sales_project_items ──< sales_project_item_measurements / _drawings / _photos >── documents
            ├──< sales_projects ──< sales_quotes ──< sales_quote_sections ──< sales_quote_section_items >── catalog_materials/catalog_slabs
            ├──< sales_quote_sections ──< sales_quote_section_measurements
            │
            ├──< orders ── quote_id ──> sales_quotes (accepted only), project_id ──> sales_projects, customer_id ──> crm_customers
            ├──< orders ──< order_sections ──< order_items / order_measurements  (independent deep copy of the source quote)
            │
            ├──< work_orders ── order_id ──> orders (1:1) ──< work_order_items >── catalog_slabs
            │
            ├──< installation_crews ──< installation_crew_members >── users
            ├──< installation_jobs ── order_id ──> orders (1:1), crew_id ──> installation_crews
            ├──< installation_jobs ──< installation_photos >── documents
            ├──< installation_notifications >── installation_job_id ──> installation_jobs, user_id ──> users
            │
            ├──< invoices ── order_id ──> orders (1:1), customer_id ──> crm_customers, installation_job_id ──> installation_jobs
            ├──< invoices ──< invoice_lines / invoice_payments
            ├──< expenses ── order_id ──> orders (nullable — null means general overhead)
            │
            ├──< communication_channels ──< communication_channel_credentials (1:1)
            ├──< communication_channels ──< communication_conversations >── crm_customers/crm_leads/sales_projects/sales_quotes/orders
            ├──< communication_conversations ──< communication_messages ──< communication_message_attachments >── documents
            ├──< communication_conversations ──< communication_conversation_notes
            ├──< communication_messages ──< communication_message_queue (retry queue)
            ├──< communication_channels ──< communication_integration_logs
            │
            ├──< ai_recommendations (owned by the `ai` module, not core — polymorphic related_entity_type/id)
            │
            ├──< suppliers ──< purchase_orders ──< purchase_order_lines >── catalog_materials
            ├──< purchase_order_lines ──< goods_receipts >── catalog_slabs (created on receipt, when slab details given)
            │
            ├──< campaigns (Marketing) ── attributed via crm_leads.campaign_id (opaque, no DB-level FK) and orders.customer_id
            │
            ├──< customer_portal_logins ── customer_id ──> crm_customers (1:1, real FK)
            │
            ├──< documents >── related_entity (any module's entity, polymorphic)
            ├──< audit_log >── actor_user_id ──> users
            └──< event_log >── company_id (mandatory on every event)

ai_jobs (core, reserved at Phase 1) — unused in production; the AI module writes exclusively to its own
ai_recommendations table instead. Kept here only because dropping it is a deliberate future decision, not
made yet.
```

## 3. Core Tables (own no module — shared platform tables)

### 3.1 `companies`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | TEXT | NOT NULL |
| slug | TEXT | NOT NULL, UNIQUE |
| currency | TEXT(3) | NOT NULL, DEFAULT `AZN` |
| locale | TEXT | NOT NULL, DEFAULT `en` |
| logo_url | TEXT | nullable |
| enabled_modules | JSON (list of strings) | NOT NULL, DEFAULT `[]` |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

Seeded rows: G-STONE GALLERY, KORONA PREMIUM, NEOLITH BAKU.

### 3.2 `users`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| email | TEXT | NOT NULL, UNIQUE, indexed |
| password_hash | TEXT | NOT NULL |
| full_name | TEXT | NOT NULL |
| is_active | BOOLEAN | NOT NULL, DEFAULT `true` |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**No column exists for refresh-token revocation** (Version 2.22.0) — see §3.7 note below; that feature lives entirely outside this table.

### 3.3 `user_company_roles`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | NOT NULL, REFERENCES users(id) **ON DELETE CASCADE**, indexed |
| company_id | UUID | NOT NULL, REFERENCES companies(id) **ON DELETE CASCADE**, indexed |
| role | TEXT | NOT NULL — one of `owner`/`manager`/`rep`/`viewer` |
| module_permissions | JSON (dict) | NOT NULL, DEFAULT `{}` — per-module role override |

**Constraints**: UNIQUE (`user_id`, `company_id`). This is the **only** table in the entire schema whose FKs declare `ON DELETE CASCADE` — every other FK in the system omits it (§1).

### 3.4 `documents`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| module | TEXT | NOT NULL |
| related_entity_type | TEXT | NOT NULL, indexed |
| related_entity_id | UUID | NOT NULL, indexed — polymorphic, no DB-level FK |
| storage_path | TEXT | NOT NULL |
| mime_type | TEXT | NOT NULL |
| uploaded_by | UUID | NOT NULL, REFERENCES users(id) |
| created_at | TIMESTAMPTZ | NOT NULL |

Every module's file attachments (Catalog material images/docs, Sales drawings/photos, Installation photos, Communication message attachments, CRM customer attachments) are thin join rows pointing here — one shared upload/storage pipeline, no per-module file handling code.

### 3.5 `audit_log`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| module | TEXT | NOT NULL |
| actor_user_id | UUID | NOT NULL, REFERENCES users(id) |
| action | TEXT | NOT NULL |
| entity_type | TEXT | NOT NULL, indexed |
| entity_id | UUID | NOT NULL, indexed |
| diff_json | JSON | nullable |
| created_at | TIMESTAMPTZ | NOT NULL |

Append-only by convention (enforced at the application layer — every write use case in every module calls `record_audit(...)` immediately after its own commit; no DB trigger prevents UPDATE/DELETE).

### 3.6 `event_log`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| event_name | TEXT | NOT NULL, indexed |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| payload | JSON | NOT NULL |
| published_by_module | TEXT | NOT NULL |
| processed_by | JSON (list of strings) | NOT NULL, DEFAULT `[]` |
| occurred_at | TIMESTAMPTZ | NOT NULL |

Append-only, same convention as `audit_log`. Every committing use case in every module publishes an event immediately after its own commit — verified 100% consistent across all modules during the `PROJECT_AUDIT.md` review.

### 3.7 `ai_jobs` — reserved at Phase 1, confirmed unused in production
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| module | TEXT | NOT NULL |
| job_type | TEXT | NOT NULL |
| status | TEXT | NOT NULL, DEFAULT `queued` |
| input_ref | TEXT | nullable |
| result_json | JSON | nullable |
| celery_task_id | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL |
| completed_at | TIMESTAMPTZ | nullable |

**Correction from the previous revision of this document**: this table was reserved in Phase 1 for the future AI module. When the AI Sales Assistant actually shipped (Version 2.8), it defined and exclusively uses its own table, `ai_recommendations` (§12.1, owned by `modules/ai/`, not `core/`) — a grep across the entire backend confirms `ai_jobs`/`AIJob` has zero read/write call sites outside its own model file and original migration. It is not populated by anything today. Left in place (dropping it is a deliberate future decision, not made yet) rather than silently removed from this document.

**Refresh-token revocation (Version 2.22.0) — infrastructure state, not a table.** `core/auth/token_denylist.py` implements a per-user **generation counter**, not a database column: a Redis key (`auth:token_generation:{user_id}`, incremented via `INCR` on logout) when Redis is reachable, with an automatic in-process `Dict`-based fallback (a module-level singleton, doesn't survive a restart or span multiple app instances) when it isn't. Every refresh token is stamped with a `gen` claim at issue time; the refresh endpoint rejects any token whose `gen` is older than the user's current counter. No migration was ever needed for this feature — it deliberately lives outside the relational schema.

## 4. CRM Module Tables

The real, shipped CRM is a **Customer / Lead / Task** model, not the generic Contact/Account/Deal/Pipeline-Stage design a previous revision of this document sketched for Phase 1 (which was never built that way — there is no `accounts`, `deals`, or `pipeline_stages` table anywhere in this codebase).

### 4.1 `crm_customers` — a sales-pipeline customer record (individual or business)
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| name | TEXT | NOT NULL |
| type | TEXT | NOT NULL, DEFAULT `individual` — `individual`\|`business` |
| primary_contact_id | UUID | nullable, REFERENCES crm_contacts(id) — **circular FK**, see §4.2 |
| assigned_manager_id | UUID | nullable, REFERENCES users(id) |
| lead_source | TEXT | nullable |
| advertising_campaign | TEXT | nullable |
| phone / whatsapp / instagram / facebook / email / address / company_name | TEXT | all nullable |
| notes | TEXT | nullable |
| status | TEXT | NOT NULL, DEFAULT `new_inquiry`, indexed |
| tags | JSON (list of strings) | NOT NULL, DEFAULT `[]` |
| created_by | UUID | nullable, REFERENCES users(id) |
| deleted_at | TIMESTAMPTZ | nullable — soft delete |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes**: `company_id`, `status` (single-column), plus composites `(company_id, status)` and `(company_id, lead_source)` — added by migration `e042f8386f09` once the actual `CustomerRepository.list()` filter combinations were known.
**`status`** (`CUSTOMER_STATUS_ORDER`, 14 values, no separate configurable table): `new_inquiry` → `contacted` → `measurement_scheduled` → `measurement_completed` → `preparing_quote` → `quote_sent` → `waiting_for_decision` → `approved` → `payment_received` → `in_production` → `installation_scheduled` → `installed` → `completed`, with `lost` reachable from any stage as a terminal state. This is a hardcoded Python list in the domain layer, not per-company-configurable data — the "configurable pipeline stages" capability named in earlier planning documents was never built.

### 4.2 `crm_contacts` — a secondary contact person, optionally linked to a Customer
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| customer_id | UUID | nullable, REFERENCES crm_customers(id), indexed |
| full_name | TEXT | NOT NULL |
| email / phone / source | TEXT | nullable |
| tags | JSON (list of strings) | NOT NULL, DEFAULT `[]` |
| created_by | UUID | nullable, REFERENCES users(id) |
| deleted_at | TIMESTAMPTZ | nullable |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Circular FK, confirmed real**: `crm_customers.primary_contact_id → crm_contacts.id` and `crm_contacts.customer_id → crm_customers.id` reference each other. Both columns are nullable, so it works correctly today and passes every test, but `alembic check` emits a SQLAlchemy table-sort warning about the cycle ("may raise an error in a future release") — a known, low-severity item for a future SQLAlchemy upgrade, not an active bug (`PROJECT_AUDIT.md` B5).

### 4.3 `crm_leads` — a pre-conversion inbound inquiry
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| full_name | TEXT | NOT NULL |
| email / phone | TEXT | nullable |
| source_channel | TEXT | NOT NULL, indexed |
| campaign | TEXT | nullable — free-text label, predates the Marketing module |
| campaign_id | UUID | nullable, indexed — **no DB-level FK** (Version 2.32.0). Opaque reference into `marketing.campaigns` for real attribution; same "polymorphic reference, application-layer only" pattern as `documents.related_entity_id`/`crm_activities.related_entity_id` below, chosen specifically so CRM never has to `depends_on` the Marketing module even though Marketing's own performance queries filter leads by it |
| status | TEXT | NOT NULL, DEFAULT `new`, indexed |
| assigned_manager_id | UUID | nullable, REFERENCES users(id) |
| converted_customer_id | UUID | nullable, REFERENCES crm_customers(id) |
| converted_contact_id | UUID | nullable, REFERENCES crm_contacts(id) |
| converted_at | TIMESTAMPTZ | nullable |
| created_by | UUID | nullable, REFERENCES users(id) |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes**: composites `(company_id, status)` and `(company_id, source_channel)`, same migration as §4.1.
**`source_channel`** (`VALID_LEAD_SOURCES`, shared vocabulary with `Customer.lead_source`): `instagram`, `facebook`, `messenger`, `whatsapp`, `phone_call`, `website`, `office_visit`, `referral`, `other`.
**`status`** (`VALID_LEAD_STATUSES`, default `new`): `new`, `contacted`, `qualified`, `converted`, `disqualified`.

### 4.4 `crm_tasks` — a follow-up/reminder, optionally polymorphically linked to any entity
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| title | TEXT(200) | NOT NULL |
| description | TEXT | nullable |
| status | TEXT(20) | NOT NULL, DEFAULT `pending`, indexed |
| priority | TEXT(20) | NOT NULL, DEFAULT `medium`, indexed |
| tags | JSON (list of strings) | NOT NULL, DEFAULT `[]` |
| due_date | TIMESTAMPTZ | nullable, indexed |
| remind_at | TIMESTAMPTZ | nullable, indexed |
| assigned_to | UUID | nullable, REFERENCES users(id), indexed |
| related_entity_type | TEXT(50) | nullable, indexed — free string, no DB-level FK/enum |
| related_entity_id | UUID | nullable, indexed |
| is_recurring | BOOLEAN | NOT NULL, DEFAULT `false` |
| recurrence_rule | TEXT(20) | nullable — `daily`\|`weekly`\|`monthly`\|`yearly` |
| recurrence_interval | INTEGER | NOT NULL, DEFAULT `1` |
| recurrence_end_date | TEXT(10) | nullable |
| series_id | UUID | nullable, REFERENCES crm_tasks(id) — **self-referential**, set on every generated occurrence, null on the template |
| completed_at / cancelled_at | TIMESTAMPTZ | nullable |
| cancelled_reason | TEXT | nullable |
| reminder_sent_at / overdue_notified_at | TIMESTAMPTZ | nullable — idempotency guards so a reminder/overdue notification is never generated twice |
| created_by | UUID | nullable, REFERENCES users(id) |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**`status`** (`VALID_TASK_STATUSES`, default `pending`): `pending`, `in_progress`, `done`, `cancelled` (`done`/`cancelled` terminal; `pending`↔`in_progress` freely, either can move to `done`/`cancelled`).
**`priority`**: `low`, `medium`, `high`, `urgent`.

### 4.5 `crm_task_notifications` — in-app notification about a Task event
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| user_id | UUID | NOT NULL, REFERENCES users(id), indexed |
| notification_type | TEXT(50) | NOT NULL — `task_assigned`\|`task_reassigned`\|`task_reminder`\|`task_overdue` |
| title | TEXT(200) | NOT NULL |
| message | TEXT | NOT NULL |
| task_id | UUID | NOT NULL, REFERENCES crm_tasks(id), indexed |
| read_at | TIMESTAMPTZ | nullable |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

### 4.6 `crm_activities` — notes/calls/emails/meetings/system log entries, polymorphically linked
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| type | TEXT | NOT NULL — `note`\|`call`\|`email`\|`meeting`\|`system` |
| body | TEXT | NOT NULL |
| related_entity_type | TEXT | NOT NULL, indexed |
| related_entity_id | UUID | NOT NULL, indexed |
| created_by | UUID | NOT NULL, REFERENCES users(id) |
| created_at | TIMESTAMPTZ | NOT NULL, `server_default=now()` — **the one model without an `updated_at` column** |

Polymorphic relation enforced at the application layer only (no DB-level FK across the boundary), same pattern as `documents`.

## 5. Stone Catalog Module Tables (Version 2.0+)

_Built ahead of Sales per `ROADMAP.md`'s dependency chain. Table names prefixed `catalog_`, matching the convention every module built after Phase 1 uses._

### 5.1 `catalog_brands`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| name | TEXT | NOT NULL |
| description | TEXT | nullable |
| logo_document_id | UUID | nullable, REFERENCES documents(id) |
| status | TEXT | NOT NULL, DEFAULT `active` (`active`\|`hidden`), indexed |
| created_by | UUID | REFERENCES users(id) |

### 5.2 `catalog_collections`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| brand_id | UUID | NOT NULL, REFERENCES catalog_brands(id), indexed |
| name | TEXT | NOT NULL |
| description | TEXT | nullable |
| status | TEXT | NOT NULL, DEFAULT `active`, indexed |

### 5.3 `catalog_materials` (the sellable design/SKU — "Stone")
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| brand_id | UUID | NOT NULL, REFERENCES catalog_brands(id), indexed |
| collection_id | UUID | nullable, REFERENCES catalog_collections(id), indexed |
| name | TEXT | NOT NULL |
| material_type | TEXT | nullable (e.g. Sintered Stone, Porcelain, Quartz, Natural Marble, Natural Granite, Dekton, Ceramic) |
| color / finish / thickness_mm / dimensions / country_of_origin | TEXT | nullable — `thickness_mm`/`dimensions` are legacy free-text, kept unchanged for backward compatibility; new Materials use the normalized §5.4 option tables instead |
| description | TEXT | nullable |
| status | TEXT | NOT NULL, DEFAULT `active`, indexed |

### 5.4 `catalog_material_thicknesses` / `catalog_material_sizes` (Version 2.12)
Normalized per-Stone option lists — a Stone can be offered in several thicknesses/sizes. `catalog_material_thicknesses`: `material_id` (FK, indexed), `thickness_mm TEXT(20) NOT NULL`, `sort_order INTEGER`. `catalog_material_sizes`: `material_id` (FK, indexed), `dimensions TEXT(50) NOT NULL`, `sort_order INTEGER`. Both indexed on `company_id`/`material_id`.

### 5.5 `catalog_warehouses`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| name | TEXT | NOT NULL |
| address | TEXT | nullable |
| status | TEXT | NOT NULL, DEFAULT `active`, indexed |

### 5.6 `catalog_slabs` (individually tracked physical inventory)
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| material_id | UUID | NOT NULL, REFERENCES catalog_materials(id), indexed |
| warehouse_id | UUID | NOT NULL, REFERENCES catalog_warehouses(id), indexed |
| slab_number | TEXT | NOT NULL, indexed, UNIQUE per `(company_id, slab_number)` |
| lot_number / barcode | TEXT | nullable, indexed |
| rack_location | TEXT | nullable |
| length_mm / width_mm | NUMERIC(10,2) | nullable |
| area_m2 | NUMERIC(10,3) | nullable — computed in the application layer (`length_mm * width_mm / 1_000_000`) at create time, not a DB-generated column |
| weight_kg | NUMERIC(10,2) | nullable |
| status | TEXT | NOT NULL, DEFAULT `available`, indexed — full lifecycle as of Version 2.34.0 (Stone Fabrication Workflow Phase 1): `received`\|`available`\|`reserved`\|`in_production`\|`offcut_created`\|`consumed`\|`sold`\|`scrap`, a domain-layer transition graph (`offcut_created`/`consumed`/`sold`/`scrap` terminal). `received`/`consumed`/`offcut_created` are additive to the original five ­— existing rows/behavior for `available`/`reserved`/`in_production`/`sold`/`scrap` are unchanged |
| parent_slab_id | UUID | nullable, REFERENCES catalog_slabs(id), indexed — **Version 2.34.0.** Set on an offcut/remnant slab registered from a parent slab that was cut in Production; self-referential, no cascade |
| is_offcut | BOOLEAN | NOT NULL, DEFAULT `false` — **Version 2.34.0.** Flags a slab as a registered remnant rather than an originally-received piece; otherwise behaves as a completely normal, independently reservable `Slab` row |

A Slab is consumed by exactly one `work_order_items` row once fabrication starts (§8.2).

### 5.6a `catalog_slab_reservations` (Material Reservation, Version 2.34.0)
The durable, queryable record of "this slab is allocated to this order item" — richer than `catalog_slabs.status` alone, which only tells you a slab *is* reserved, never for whom. Owned by Catalog (not Production or Orders) so every module downstream of Catalog can create/consult reservations without Catalog ever having to depend on them.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| slab_id | UUID | NOT NULL, REFERENCES catalog_slabs(id), indexed |
| order_id | UUID | NOT NULL, indexed — **plain UUID, no FK** (the same "polymorphic reference, application-layer only" pattern already used by `documents.related_entity_id` and `crm_leads.campaign_id`), so Catalog never has to depend on Orders |
| order_item_id | UUID | NOT NULL, indexed — plain UUID, same reasoning |
| status | TEXT | NOT NULL, DEFAULT `active`, indexed — `active`\|`released`\|`consumed` (`released`/`consumed` terminal) |
| notes | TEXT | nullable |
| reserved_by | UUID | nullable, REFERENCES users(id) |
| reserved_at / released_at | TIMESTAMPTZ | nullable |

The double-booking guard (only one *active* reservation per slab) is enforced the same way this codebase already enforces comparable invariants elsewhere (PO-number sequences, Sales' own quote-acceptance slab check): a check-then-set inside one use-case execution, not a partial unique index. Orders' `CreateOrderUseCase` backfills a reservation row (`require_available=False`) for every slab-linked item copied from an accepted quote, since that slab was already moved to `reserved` at quote-acceptance time by Sales — this is the only mechanism that gives 100% reservation-record coverage without any change to the Sales module.

### 5.7 `catalog_price_lists` / `catalog_price_list_entries`
Company-specific pricing as a named header (`catalog_price_lists`: `name`, `currency` default `AZN`, `is_default`, `status`) with per-material line items (`catalog_price_list_entries`: `price_list_id`, `material_id`, `cost_price NUMERIC(14,2)`, `sale_price NUMERIC(14,2)`, `UNIQUE(price_list_id, material_id)`) — multiple price lists per company (retail vs. wholesale) rather than one price column on `catalog_materials`.

### 5.8 `catalog_material_images` / `catalog_material_documents`
Thin join tables linking a `catalog_materials` row to a core `documents` row. `catalog_material_images.image_type` ∈ `gallery`\|`thumbnail`\|`bookmatch_left`\|`bookmatch_right`; `catalog_material_documents.document_type` ∈ `technical_pdf`\|`installation_guide`\|`cleaning_guide`.

## 6. Sales Module Tables

Two parallel structures sharing the module, serving different purposes — see `API_SPECIFICATION.md` §12 for the same distinction from the endpoint side:
- **Quotes** (§6.2–6.4): a Project's versioned pricing document.
- **Project workspace** (§6.5–6.6): the physical execution plan (Rooms → Project Items → their real measurements/drawings/photos), independent of any specific Quote version.

**No `sales_orders` table exists** — Orders is an entirely separate module (§7), created from an accepted Quote as an independent, deep-copied snapshot.

### 6.1 `sales_projects` — a customer's overall project ("Layihə")
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| customer_id | UUID | NOT NULL, REFERENCES crm_customers(id), indexed |
| name | TEXT(200) | NOT NULL |
| project_type | TEXT(50) | NOT NULL, DEFAULT `other` — `kitchen`\|`bathroom`\|`commercial`\|`stairs`\|`fireplace`\|`other` |
| address | TEXT | nullable |
| notes | TEXT | nullable |
| assigned_to | UUID | nullable, REFERENCES users(id), indexed |
| status | TEXT(50) | NOT NULL, DEFAULT `active` — `active`\|`completed`\|`cancelled`, indexed |

### 6.2 `sales_quotes` — a versioned pricing document for a Project
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| project_id | UUID | NOT NULL, REFERENCES sales_projects(id), indexed |
| customer_id | UUID | NOT NULL, REFERENCES crm_customers(id), indexed |
| version | INTEGER | NOT NULL, DEFAULT `1` |
| quote_number | TEXT(50) | NOT NULL, indexed |
| status | TEXT(50) | NOT NULL, DEFAULT `draft`, indexed |
| currency | TEXT(3) | NOT NULL, DEFAULT `AZN` |
| price_list_id | UUID | nullable, REFERENCES catalog_price_lists(id) |
| valid_until | TEXT(10) | nullable |
| internal_notes / customer_notes | TEXT | nullable |
| prepared_by | UUID | nullable, REFERENCES users(id) |
| sent_at / accepted_at / rejected_at | TIMESTAMPTZ | nullable |
| subtotal_gross | NUMERIC(14,2) | NOT NULL, DEFAULT `0` |
| discount_type | TEXT(20) | NOT NULL, DEFAULT `none` — exactly `none`\|`percent`\|`fixed` |
| discount_value / discount_amount | NUMERIC(14,2) | NOT NULL, DEFAULT `0` |
| subtotal_after_discount | NUMERIC(14,2) | NOT NULL, DEFAULT `0` |
| vat_rate | NUMERIC(5,2) | NOT NULL, DEFAULT `18` |
| vat_amount | NUMERIC(14,2) | NOT NULL, DEFAULT `0` |
| total_final | NUMERIC(14,2) | NOT NULL, DEFAULT `0` |
| total_internal_cost / total_profit | NUMERIC(14,2) | NOT NULL, DEFAULT `0` — never exposed on the customer-facing PDF |
| profit_margin_pct | NUMERIC(5,2) | NOT NULL, DEFAULT `0` |

**`status`** (`VALID_QUOTE_STATUSES`, default `draft`): `draft`, `sent`, `negotiation`, `accepted`, `rejected`, `expired`. `sent`/`negotiation`/`accepted` are immutable (any edit forces a new version, hence the `version` column); `rejected`/`expired` are terminal. Transition graph: `draft→{sent, rejected}`; `sent→{negotiation, accepted, rejected, expired}`; `negotiation→{sent, accepted, rejected, expired}`; `accepted→{rejected}` (cancellation path only).

### 6.3 `sales_quote_sections` / `sales_quote_section_items` / `sales_quote_section_measurements`
Grouping within a Quote (e.g. by room), each priced line item, and each measurement row feeding that pricing:
- `sales_quote_sections`: `quote_id` (FK, indexed), `name TEXT(200)`, `sort_order`, `notes`, `total_measured_area NUMERIC(10,4)`, `subtotal_sale`/`subtotal_cost NUMERIC(14,2)`.
- `sales_quote_section_items`: `section_id`/`quote_id` (FK, indexed), `item_type TEXT(50)` (21 curated values — see `API_SPECIFICATION.md` §12), `description TEXT(500)`, `material_id`/`slab_id` (nullable FK, indexed), `quantity NUMERIC(10,3)`, `unit TEXT(10)` (`m2`\|`lm`\|`unit`), `unit_sale_price`/`unit_cost_price`/`line_total_sale`/`line_total_cost NUMERIC(14,2)`, `notes`.
- `sales_quote_section_measurements`: `section_id`/`quote_id` (FK, indexed), `label TEXT(200)`, `length_mm`/`width_mm NUMERIC(10,1)`, `thickness_mm NUMERIC(6,1)`, `quantity INTEGER`, `area_m2`/`required_area_m2 NUMERIC(10,4)`, `waste_pct NUMERIC(5,2)` default `10`, `override_required_area BOOLEAN`, `notes`.

### 6.4 `sales_quote_number_sequences`
Atomic per-company/year counter: `company_id` (FK, indexed), `year INTEGER`, `last_number INTEGER DEFAULT 0`. `UNIQUE(company_id, year)`. No timestamps. Produces numbers like `QT-2026-0001-v1`.

### 6.5 `sales_rooms` / `sales_project_items` — the Project workspace
- **`sales_rooms`**: `project_id` (FK, indexed), `room_type TEXT(50)` default `custom` (`kitchen`/`bathroom`/`living_room`/`corridor`/`balcony`/`facade`/`yard`/`custom`, plus legacy `staircase`/`exterior` kept valid on old rows), `name TEXT(200)` nullable, `notes`, `sort_order`.
- **`sales_project_items`** (a fabricated piece, "Məmulat"): `project_id` (FK, indexed, denormalized from room for project-wide queries), `room_id` (FK, indexed), `item_type TEXT(50)` default `other` (curated 12-value picker vocabulary, shared 21-value storage vocabulary with Quote items), `name TEXT(200)` nullable, `material_id` (FK catalog_materials, indexed), `material_thickness_id`/`material_size_id` (FK, indexed — **added by migration `fcaddc974e1c`, Sprint 4**, after the table's original creation), `quantity NUMERIC(10,3)`, `unit TEXT(10)`, `notes`, `production_status`/`installation_status TEXT(50)` nullable (set by the Production/Installation modules' events, no fixed enum in the Sales domain itself), `completion_status TEXT(50)` nullable (**added by migration `4cbc1f1d4028`, Sprint 5**, even later — `pending`\|`delivered`\|`accepted`, distinct from production/installation status; tracks physical handover to the customer), `sort_order`.

### 6.6 `sales_project_item_measurements` / `_drawings` / `_photos`
- **`sales_project_item_measurements`**: `project_item_id` (FK, indexed), `revision_number INTEGER` default `1` — **every new measurement is a new revision, never an overwrite**, `status TEXT(20)` default `draft` (`draft`\|`final`), `length_mm`/`width_mm NUMERIC(10,1)`, `thickness_mm NUMERIC(6,1)`, `quantity INTEGER`, `area_m2 NUMERIC(10,4)`, `measurer_name TEXT(200)` default `""` (free text — the measurer is often a field installer with no system login), `measured_at DATE` nullable, `notes`, `customer_signature_document_id` (FK documents, nullable), `created_by`.
- **`sales_project_item_drawings`**: `project_item_id` (FK, indexed), `document_id` (FK documents, indexed), `drawing_type TEXT(20)` default `sketch` (`dwg`\|`dxf`\|`sketch`\|`pdf`), `label`, `sort_order`, `uploaded_by`.
- **`sales_project_item_photos`**: `project_item_id` (FK, indexed), `document_id` (FK documents, indexed), `caption TEXT(200)` nullable, `sort_order`, `uploaded_by`.

### 6.7 `company_service_prices`
Per-company default sale/cost price for a non-material service key: `company_id` (FK, indexed), `service_key TEXT(100)`, `sale_price`/`cost_price NUMERIC(14,2)` default `0`. `UNIQUE(company_id, service_key)` — upsert semantics. `service_key` ∈ `edge_profile_per_lm`, `sink_cutout`, `cooktop_cutout`, `faucet_hole`, `installation_per_m2`, `transport`, `crane`.

## 7. Orders Module Tables

An Order is created from a single **accepted** Quote and deep-copies its Sections/Items/Measurements into its own independent, mutable tables at that moment (confirmed in `CreateOrderUseCase` — the Quote is never touched again, and editing the Order afterward never touches the source Quote). Table names are **not** prefixed `orders_` — they are simply `orders`, `order_sections`, `order_items`, `order_measurements`.

### 7.1 `orders`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| project_id | UUID | NOT NULL, REFERENCES sales_projects(id), indexed |
| customer_id | UUID | NOT NULL, REFERENCES crm_customers(id), indexed |
| quote_id | UUID | NOT NULL, REFERENCES sales_quotes(id), indexed |
| order_number | TEXT(50) | NOT NULL, indexed |
| status | TEXT(50) | NOT NULL, DEFAULT `waiting`, indexed |
| currency | TEXT(3) | NOT NULL, DEFAULT `AZN` |
| notes / production_notes / installation_notes | TEXT | nullable |
| delivery_address | TEXT(500) | nullable |
| scheduled_production_date / scheduled_installation_date | TEXT(10) | nullable |
| completed_at / cancelled_at | TIMESTAMPTZ | nullable |
| cancelled_reason | TEXT | nullable |
| created_by | UUID | nullable, REFERENCES users(id) |
| subtotal_gross, discount_type/value/amount, subtotal_after_discount, vat_rate/amount, total_final, total_internal_cost, total_profit | (same shape as `sales_quotes`) | a **financial snapshot copied from the Quote at creation time**, not a live reference |

**`status`** (`VALID_ORDER_STATUSES`, default `waiting`): `waiting`, `measuring`, `approved_for_production`, `in_production`, `ready`, `delivered`, `installed`, `completed`, `cancelled` (`completed`/`cancelled` terminal). Transition graph: `waiting→{measuring, approved_for_production, cancelled}`; `measuring→{approved_for_production, cancelled}`; `approved_for_production→{in_production, cancelled}`; `in_production→{ready, cancelled}`; `ready→{delivered, installed, cancelled}`; `delivered→{installed, cancelled}`; `installed→{completed, cancelled}`.

### 7.2 `order_sections` / `order_items` / `order_measurements`
Structurally identical to `sales_quote_sections`/`sales_quote_section_items`/`sales_quote_section_measurements` (§6.3) — same columns, copied at Order-creation time, then independently mutable. `order_items` additionally carries its own `production_status`/`installation_status TEXT(50)` (set via `PATCH /orders/{id}/items/{item_id}` as Production/Installation progress).

### 7.3 `order_number_sequences`
Same shape as `sales_quote_number_sequences` (§6.4): `company_id`, `year`, `last_number`, `UNIQUE(company_id, year)`, no timestamps.

## 8. Production Module Tables

One `work_orders` row ("Production Job") per Order (1:1, gated on the Order reaching `approved_for_production`), consuming every slab-linked Order Item via a join row. **Version 2.34.0 (Stone Fabrication Workflow Phase 1)** added `priority`/`current_stage_id` to `work_orders`, plus two new tables (`production_stages`, `work_order_events`) — all additive; the pre-existing `status` lifecycle and its Order/slab cascades are unchanged.

### 8.1 `work_orders`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| order_id | UUID | NOT NULL, REFERENCES orders(id), **UNIQUE**, indexed |
| work_order_number | TEXT(50) | NOT NULL, indexed |
| status | TEXT(50) | NOT NULL, DEFAULT `queued`, indexed |
| priority | TEXT(10) | NOT NULL, DEFAULT `normal`, indexed — **Version 2.34.0.** `low`\|`normal`\|`high`\|`urgent`, a simple shop-floor triage vocabulary, not a numeric weight |
| current_stage_id | UUID | nullable, REFERENCES production_stages(id), indexed — **Version 2.34.0.** Independent of `status`: a finer-grained position within the company's configurable stage pipeline (§8.4), not gated by or driving the status transitions below |
| assigned_to | UUID | nullable, REFERENCES users(id) |
| scheduled_start_date / scheduled_completion_date | TEXT(10) | nullable — `scheduled_completion_date` doubles as the job's "due date" in the UI (Version 2.34.0), no separate column |
| completed_at / cancelled_at | TIMESTAMPTZ | nullable |
| cancelled_reason / notes | TEXT | nullable |
| created_by | UUID | nullable, REFERENCES users(id) |

**`status`** (default `queued`): `queued` → `cutting` → `polishing` → `quality_check` → `completed`, with `cancelled` reachable from any non-terminal state; `completed`/`cancelled` terminal.

### 8.2 `work_order_items`
One row per slab consumed. `work_order_id` (FK, indexed), `order_item_id` (FK order_items, **UNIQUE**, indexed — one work-order item per order item), `slab_id` (FK catalog_slabs, indexed). Completing the parent work order moves its slabs to the terminal `consumed` status (Version 2.34.0 — previously `sold`; a slab already moved on a different way, e.g. registered as an offcut mid-job, is left untouched) and marks the corresponding `catalog_slab_reservations` rows `consumed`, marks each item's `production_status: done` on the Order, and advances the Order to `ready`; cancelling releases slabs back to `available` and their reservations to `released`.

### 8.3 `work_order_number_sequences`
Same shape as §6.4/§7.3: `company_id`, `year`, `last_number`, `UNIQUE(company_id, year)`.

### 8.4 `production_stages` (configurable pipeline, Version 2.34.0)
Per-company, freely renamable/reorderable/hideable — not a hardcoded enum. Lazily seeded with 8 stone-fabrication defaults (Measuring, Design, CNC, Waterjet, Cutting, Polishing, Quality Control, Ready for Installation) the first time a company's stage list is requested and none exist yet.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| name | TEXT(100) | NOT NULL, **UNIQUE** per `(company_id, name)` |
| sort_order | INTEGER | NOT NULL, DEFAULT `0` |
| is_active | BOOLEAN | NOT NULL, DEFAULT `true` |

### 8.5 `work_order_events` (production timeline, Version 2.34.0)
One row per change to a work order's status/stage/priority/assigned operator — the backbone of the "complete production timeline" requirement, sitting *alongside*, not instead of, the mandatory `core.audit_log` entry every one of these writes already records. Deliberately denormalized (`from_value`/`to_value` as display strings, e.g. a stage's `name` rather than its id) so a timeline UI renders directly without re-joining at read time.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| work_order_id | UUID | NOT NULL, REFERENCES work_orders(id), indexed |
| event_type | TEXT(30) | NOT NULL — `created`\|`status_changed`\|`stage_changed`\|`priority_changed`\|`operator_assigned` |
| from_value / to_value | TEXT(200) | nullable |
| notes | TEXT | nullable |
| changed_by | UUID | nullable, REFERENCES users(id) |
| changed_at | TIMESTAMPTZ | nullable |

## 9. Installation Module Tables

One `installation_jobs` row per Order (1:1, gated on the Order reaching `ready`/`delivered`).

### 9.1 `installation_crews` / `installation_crew_members`
- **`installation_crews`**: `company_id` (indexed), `name TEXT(200)`, `status TEXT(20)` default `active` (`active`\|`inactive`), `notes`, `created_by`.
- **`installation_crew_members`** (many-to-many join): `crew_id`/`user_id` (FK, both indexed), `is_lead BOOLEAN` default `false`. `UNIQUE(crew_id, user_id)` — one row per membership, `is_lead` flag rather than a separate lead FK on the crew.

### 9.2 `installation_jobs`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| order_id | UUID | NOT NULL, REFERENCES orders(id), **UNIQUE**, indexed |
| job_number | TEXT(50) | NOT NULL, indexed |
| status | TEXT(50) | NOT NULL, DEFAULT `scheduled`, indexed |
| crew_id | UUID | nullable, REFERENCES installation_crews(id), indexed |
| scheduled_date | TEXT(10) | nullable, indexed |
| scheduled_time_slot | TEXT(50) | nullable |
| route_sequence | INTEGER | nullable |
| started_at / completed_at / cancelled_at | TIMESTAMPTZ | nullable |
| cancelled_reason / notes / completion_notes | TEXT | nullable |
| created_by | UUID | nullable |

**`status`** (default `scheduled`): `scheduled` → `en_route` → `in_progress` → `completed`, with `cancelled` reachable from `scheduled`/`en_route`/`in_progress`; `completed`/`cancelled` terminal. Completing a job cascades `installation_status: done` onto every Order item and advances the Order to `installed`, mirroring Production's pattern exactly.

### 9.3 `installation_photos`
Photo or captured signature attached to a job, backed by the shared `documents` table: `installation_job_id` (FK, indexed), `document_id` (FK, indexed), `photo_type TEXT(20)` default `other` (`before`\|`after`\|`damage`\|`signature`\|`other`), `caption TEXT(500)` nullable, `sort_order`. A customer's captured signature is a photo row with `photo_type="signature"`, not a separate entity.

### 9.4 `installation_notifications`
In-app notification about a job event, for one user: `user_id` (FK, indexed), `notification_type TEXT(50)` (`job_assigned`\|`job_rescheduled`\|`job_status_changed`), `title TEXT(200)`, `message TEXT`, `installation_job_id` (FK, nullable, indexed), `read_at` nullable. **No email/SMS delivery exists anywhere in this codebase** — this in-app table is the entire, real "notifications" feature, per the model's own docstring.

### 9.5 `installation_job_number_sequences`
Same shape as §6.4/§7.3/§8.3.

## 10. Finance Module Tables

### 10.1 `invoices`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed (denormalized from Order) |
| order_id | UUID | NOT NULL, REFERENCES orders(id), **UNIQUE**, indexed |
| customer_id | UUID | NOT NULL, REFERENCES crm_customers(id), indexed (denormalized from Order) |
| installation_job_id | UUID | nullable, REFERENCES installation_jobs(id), indexed |
| invoice_number | TEXT(50) | NOT NULL, indexed |
| status | TEXT(50) | NOT NULL, DEFAULT `draft`, indexed |
| currency | TEXT(3) | NOT NULL, DEFAULT `AZN` |
| subtotal_amount / total_amount / amount_paid | NUMERIC(14,2) | NOT NULL, DEFAULT `0` |
| issue_date | TEXT(10) | NOT NULL |
| due_date | TEXT(10) | nullable |
| notes | TEXT | nullable |
| sent_at / paid_at / cancelled_at | TIMESTAMPTZ | nullable |
| cancelled_reason | TEXT | nullable |
| created_by | UUID | nullable |

**`balance_due` is not a stored column** — a Python `@property` computed as `total_amount - amount_paid`. `amount_paid` **is** stored, recalculated as a running sum each time a payment is recorded.
**`status`** (default `draft`): `draft`, `sent`, `partially_paid`, `paid`, `overdue`, `cancelled` (`paid`/`cancelled` terminal). Transition graph: `draft→{sent, cancelled}`; `sent→{partially_paid, paid, overdue, cancelled}`; `partially_paid→{paid, overdue, cancelled}`; `overdue→{partially_paid, paid, cancelled}`. Manually settable via the status endpoint: only `sent`/`overdue`/`cancelled` — `partially_paid`/`paid` are set exclusively as a side effect of `RecordPaymentUseCase`, so `amount_paid` and `status` can never drift apart. An Order becomes invoiceable once it reaches `ready`/`delivered`/`installed`/`completed`.

### 10.2 `invoice_lines`
Point-in-time snapshot line copied from the order's items at invoice creation — plain description/amount, no live FK back to `order_items`: `invoice_id` (FK, indexed), `description TEXT(500)`, `amount NUMERIC(14,2)` default `0`, `sort_order`.

### 10.3 `invoice_payments`
A single payment recorded against an invoice (an invoice can have several): `invoice_id` (FK, indexed), `amount NUMERIC(14,2)` NOT NULL, `method TEXT(20)` default `cash` (`cash`\|`bank_transfer`\|`card`\|`check`\|`other`), `paid_at TIMESTAMPTZ` NOT NULL, `reference_note TEXT` nullable, `recorded_by` nullable.

### 10.4 `invoice_number_sequences`
Same shape as §6.4/§7.3/§8.3/§9.5.

### 10.5 `expenses`
A company or order-linked cost entry: `company_id` (indexed), `order_id` (FK, **nullable** — null means general overhead, not tied to a job, indexed), `category TEXT(20)` default `other` (`materials`\|`labor`\|`transport`\|`utilities`\|`rent`\|`other`, indexed), `description TEXT` nullable, `amount NUMERIC(14,2)` NOT NULL, `currency TEXT(3)` default `AZN`, `expense_date TEXT(10)` NOT NULL, `created_by` nullable.

## 11. Communication Center Module Tables (Version 2.7+ Real Integrations)

_Unified omnichannel inbox (WhatsApp Business, Instagram Direct, Facebook Messenger, Email, SMS) integrated with CRM. Real WhatsApp/Instagram/Messenger (Meta Graph API), SMTP/IMAP, and Twilio SMS providers (Version 2.9) sit on top of `communication_channels` without changing its shape — a channel with no `communication_channel_credentials` row keeps using `NullChannelProvider` exactly as in Version 2.7._

### 11.1 `communication_channels`
`company_id` (indexed), `channel_type TEXT` (`whatsapp`\|`instagram`\|`messenger`\|`email`\|`sms`, indexed), `display_name TEXT` NOT NULL, `identifier TEXT` nullable (the channel's own phone/email/handle), `is_active BOOLEAN` default `true`, `created_by`. A company may have several rows of the same `channel_type` (e.g. multiple WhatsApp numbers) — no one-per-type uniqueness constraint.

### 11.2 `communication_conversations`
`channel_id` (FK, indexed), `customer_id`/`lead_id`/`project_id`/`quote_id`/`order_id` (all nullable FK, indexed — to `crm_customers`, `crm_leads`, `sales_projects`, `sales_quotes`, `orders` respectively), `external_contact_id TEXT` NOT NULL indexed (the counterpart's channel address), `external_contact_name TEXT` nullable, `status TEXT` default `open` (`open`\|`pending`\|`closed`, indexed, freely reachable from one another), `assigned_to` (FK, indexed), `tags JSON` default `[]`, `unread_count INTEGER` default `0`, `last_message_at TIMESTAMPTZ` indexed, `last_message_preview TEXT(300)`, `created_by`. One conversation per `(company_id, channel_id, external_contact_id)`. `customer_id`/`lead_id` populated by matching the sender against an existing Customer's mapped contact field (`whatsapp`→`Customer.whatsapp`, etc.), auto-creating a Lead if no match.

### 11.3 `communication_messages`
`conversation_id` (FK, indexed), `direction TEXT` (`inbound`\|`outbound`, indexed), `sender_type TEXT` (`customer`\|`agent`\|`system`), `sender_user_id` nullable (set for outbound agent messages), `message_type TEXT` default `text` (`text`\|`image`\|`document`\|`audio`\|`video`\|`template`), `body TEXT` nullable, `template_id` (FK, nullable), `external_message_id TEXT` nullable (the real provider-assigned id since Version 2.9; a local placeholder before then), `status TEXT` default `sent` (`received`\|`sent`\|`delivered`\|`read`\|`failed`).

### 11.4 `communication_message_attachments` / `communication_conversation_notes` / `communication_message_templates`
- **`communication_message_attachments`**: thin join, `message_id`/`document_id` (FK), `file_name` nullable.
- **`communication_conversation_notes`**: internal, customer-invisible: `conversation_id` (FK), `body TEXT` NOT NULL, `created_by`.
- **`communication_message_templates`**: `name TEXT`, `channel_type TEXT` nullable indexed (`null` = usable on any channel), `shortcut TEXT` nullable indexed (a quick-reply trigger), `body TEXT` NOT NULL, `is_active BOOLEAN` default `true`, `created_by`. Covers both "templates" and "quick replies" as one entity, distinguished only by whether `shortcut` is set.

### 11.5 `communication_channel_credentials` (Version 2.9)
`channel_id` (FK, **UNIQUE**, indexed — at most one credential per channel), `provider TEXT(30)` NOT NULL (`meta_whatsapp`\|`meta_instagram`\|`meta_messenger`\|`smtp`\|`twilio_sms`\|`webhook`), `encrypted_config TEXT` NOT NULL (Fernet-encrypted JSON — host/port/account ids/tokens, never returned unencrypted), `webhook_secret_encrypted TEXT` nullable, `imap_last_synced_uid INTEGER` nullable (the sync cursor for `email` channels), `health_status TEXT(20)` default `unknown` (`unknown`\|`ok`\|`error`), `last_checked_at`/`last_error` nullable, `created_by`.

### 11.6 `communication_message_queue` (Version 2.9)
`message_id` (FK, indexed), `channel_id` (FK, indexed), `status TEXT(20)` default `pending` (`pending`\|`processing`\|`sent`\|`failed`, indexed), `attempts INTEGER` default `0`, `max_attempts INTEGER` default `5`, `next_attempt_at TIMESTAMPTZ` nullable indexed, `last_error TEXT` nullable. A failed real-provider send never surfaces as a 500 — the Message is recorded `failed` and a row is created here for the retry endpoint (exponential backoff, permanently `failed` after `max_attempts`).

### 11.7 `communication_integration_logs` (Version 2.9)
`channel_id` (FK, nullable, indexed), `provider TEXT(30)` indexed, `direction TEXT(10)` (`outbound`\|`inbound`, indexed), `action TEXT(30)` indexed (`send_message`\|`test_connection`\|`queue_retry`\|`imap_sync`\|`receive_webhook`), `success BOOLEAN`, `status_code INTEGER` nullable, `signature_valid BOOLEAN` nullable (set only for `direction=inbound`), `error_message TEXT` nullable, `duration_ms INTEGER` nullable, `payload JSON` nullable. One table, discriminated by `direction`/`action`, backs Provider Diagnostics, Logs, and the Webhook Monitor at once. A rejected webhook signature is still logged (`success=false`, `signature_valid=false`), not dropped.

## 12. AI Sales Assistant Module Tables (Version 2.8+)

### 12.1 `ai_recommendations`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| analysis_kind | TEXT | NOT NULL, indexed — `lead`\|`conversation`\|`quote`\|`task` |
| recommendation_type | TEXT | NOT NULL, indexed — one of 27 values across CRM/Communication/Sales/Task Intelligence |
| related_entity_type / related_entity_id | TEXT / UUID | nullable, indexed |
| provider | TEXT | NOT NULL, DEFAULT `mock`, indexed |
| model | TEXT | NOT NULL, DEFAULT `""` |
| prompt | TEXT | NOT NULL |
| response | JSON | NOT NULL — the provider's full structured output |
| confidence_score | NUMERIC(4,3) | nullable |
| execution_time_ms | INTEGER | nullable |
| summary | TEXT(500) | nullable |
| status | TEXT | NOT NULL, DEFAULT `pending`, indexed — `pending`\|`accepted`\|`rejected`\|`edited` |
| edited_response | JSON | nullable |
| requested_by / reviewed_by | UUID | nullable, REFERENCES users(id) |
| reviewed_at | TIMESTAMPTZ | nullable |

**This table is owned by `modules/ai/`, not `core/`** — it is entirely separate from the reserved-but-unused core `ai_jobs` table (§3.7). One table covers all 27 recommendation types, discriminated by `recommendation_type`, the same pattern `communication_message_templates` uses. **Nothing in this module ever writes to another module's tables** — accepting/rejecting/editing a recommendation only ever updates this table's own `status`/`reviewed_by`/`reviewed_at`/`edited_response` columns, making "AI never performs business actions automatically" a structural property, not a UI convention.

## 13. Purchasing Module Tables (Version 2.31.0)

_Suppliers and purchase orders, closing the restocking loop for the Stone Catalog — the inverse of Production's slab-consumption flow (§8.2). Receiving against a line optionally creates a real `catalog_slabs` row via the same `CreateSlabUseCase` Catalog itself uses, rather than duplicating slab-creation logic._

### 13.1 `suppliers`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| name | TEXT | NOT NULL |
| contact_name / phone / email | TEXT | nullable |
| address / notes | TEXT | nullable |
| status | TEXT | NOT NULL, DEFAULT `active` (`active`\|`hidden`), indexed |
| created_by | UUID | nullable, REFERENCES users(id) |

### 13.2 `purchase_orders`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| supplier_id | UUID | NOT NULL, REFERENCES suppliers(id), indexed |
| po_number | TEXT(50) | NOT NULL, indexed |
| status | TEXT(50) | NOT NULL, DEFAULT `draft`, indexed |
| currency | TEXT(3) | NOT NULL, DEFAULT `AZN` |
| notes | TEXT | nullable |
| expected_delivery_date | TEXT(10) | nullable |
| subtotal_amount / total_amount | NUMERIC(14,2) | NOT NULL, DEFAULT `0` — no separate VAT modeling, unlike Sales Quotes/Orders (a deliberately simpler cost-side document) |
| cancelled_at | TIMESTAMPTZ | nullable |
| cancelled_reason | TEXT | nullable |
| created_by | UUID | nullable, REFERENCES users(id) |

**`status`** (default `draft`): `draft`, `sent`, `confirmed`, `partially_received`, `received`, `cancelled` (`received`/`cancelled` terminal). Transition graph: `draft→{sent, cancelled}`; `sent→{confirmed, cancelled}`; `confirmed→{partially_received, received, cancelled}`; `partially_received→{received, cancelled}`. Only `sent`/`confirmed`/`cancelled` are manually settable — `partially_received`/`received` are set exclusively as a side effect of receiving (§13.4), the same discipline Finance's `invoice.status` uses for `partially_paid`/`paid` (§10.1). Only a `draft` order's lines/notes/expected-delivery-date may still change.

### 13.3 `purchase_order_lines`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| purchase_order_id | UUID | NOT NULL, REFERENCES purchase_orders(id), indexed |
| material_id | UUID | nullable, REFERENCES catalog_materials(id), indexed — nullable so a line can be a non-material cost (freight, customs) |
| description | TEXT(500) | NOT NULL, DEFAULT `""` |
| quantity | NUMERIC(10,3) | NOT NULL, DEFAULT `1` |
| unit | TEXT(10) | NOT NULL, DEFAULT `unit` |
| unit_cost / line_total | NUMERIC(14,2) | NOT NULL, DEFAULT `0` |
| quantity_received | NUMERIC(10,3) | NOT NULL, DEFAULT `0` — accumulates across every `goods_receipts` row against this line; never exceeds `quantity` (enforced in the use case, not a DB constraint) |
| sort_order | INTEGER | NOT NULL, DEFAULT `0` |

### 13.4 `goods_receipts`
One receiving action recorded against a line.
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, indexed |
| purchase_order_id | UUID | NOT NULL, REFERENCES purchase_orders(id), indexed — denormalized from the line for direct per-order queries |
| purchase_order_line_id | UUID | NOT NULL, REFERENCES purchase_order_lines(id), indexed |
| slab_id | UUID | nullable, REFERENCES catalog_slabs(id), indexed — set only when the receiver supplied warehouse + slab details and the line has a linked material |
| quantity_received | NUMERIC(10,3) | NOT NULL |
| notes | TEXT | nullable |
| received_by | UUID | nullable, REFERENCES users(id) |
| received_at | TIMESTAMPTZ | NOT NULL |

### 13.5 `purchase_order_number_sequences`
Same shape as every other module's number sequence (§6.4/§7.3/§8.3/§9.5/§10.4): `company_id`, `year`, `last_number`, `UNIQUE(company_id, year)`, no timestamps. Produces numbers like `PO-2026-0001`.

## 14. Marketing Module Tables (Version 2.32.0)

_Marketing campaigns with real, ID-based lead attribution and revenue performance — not the free-text `crm_leads.campaign`/`crm_customers.advertising_campaign` fields, which predate this module and remain untouched. `depends_on=["crm", "orders"]`, read-only: the performance calculation queries `crm_leads`/`orders` directly rather than duplicating their data, the same "depends_on for read access" pattern Reports uses against every other module._

### 14.1 `campaigns`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| name | TEXT | NOT NULL |
| channel | TEXT | NOT NULL, indexed — same vocabulary as `crm_leads.source_channel` (§4.3) |
| status | TEXT | NOT NULL, DEFAULT `draft`, indexed |
| start_date / end_date | TEXT(10) | nullable |
| budget | NUMERIC(14,2) | nullable |
| currency | TEXT(3) | NOT NULL, DEFAULT `AZN` |
| notes | TEXT | nullable |
| created_by | UUID | nullable, REFERENCES users(id) |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**`status`** (default `draft`): `draft`, `active`, `completed`, `cancelled` (`completed`/`cancelled` terminal). Transition graph: `draft→{active, cancelled}`; `active→{completed, cancelled}`. Only a non-terminal campaign's `name`/`channel`/`start_date`/`end_date`/`budget`/`notes` may still change.

**Performance (not a table — computed on read by `CampaignPerformanceRepository`)**: `leads_count` = count of `crm_leads` rows with this campaign's id in `campaign_id` (§4.3), scoped by `company_id`; `converted_count` = of those, how many have `converted_customer_id` set; `conversion_rate` = `converted_count / leads_count`; `attributed_revenue` = sum of `orders.total_final` for orders belonging to those converted customers, counting only orders whose status is in `{ready, delivered, installed, completed}` — a cancelled order never inflates a campaign's apparent ROI.

## 15. Customer Portal Module Tables (Version 2.33.0)

_A module beyond the original ten-module plan — same category as Communication Center (§11). Gives a G-STONE customer (not a staff member) their own login to see their own orders, quotes, invoices, installation schedule, and documents. `depends_on=["crm", "sales", "orders", "finance", "installation"]`: `customer_portal_logins` carries a real FK to `crm_customers.id` (safe here — unlike `crm_leads.campaign_id` in §14 — because this table lives in the *dependent* module, not in CRM), and the customer-facing read endpoints query Order/Quote/Invoice/InstallationJob directly, the same "depends_on for read access" pattern §14 and Reports (§12's sibling) use._

### 15.1 `customer_portal_logins`
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | NOT NULL, REFERENCES companies(id), indexed |
| customer_id | UUID | NOT NULL, UNIQUE, REFERENCES crm_customers(id), indexed — one login per customer |
| email | TEXT | NOT NULL, UNIQUE, indexed — globally unique, same as staff `users.email` (§3) |
| password_hash | TEXT | NOT NULL — bcrypt via the same `core.auth.security.hash_password` staff accounts use |
| is_active | BOOLEAN | NOT NULL, DEFAULT `true` |
| last_login_at | TIMESTAMPTZ | nullable |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**A separate identity from `users`, deliberately.** A customer is not a member of any company's RBAC hierarchy (`user_company_roles`, §3) — they have exactly one `customer_id`, not a role or `module_permissions`. JWTs issued for this identity carry `"type": "customer_access"`/`"customer_refresh"` (vs. staff's `"access"`/`"refresh"`) and only `customer_id`/`company_id` claims, checked by `customer_portal`'s own `get_current_customer` dependency — structurally incapable of being accepted by `core.rbac.dependencies.get_current_user` or vice versa, confirmed by tests exercising both directions.

**No new tables for Orders/Quotes/Invoices/InstallationJobs/Documents.** The customer-facing read endpoints query the existing tables from §6 (`sales_quotes`), §7 (`orders`), §9 (`installation_jobs`), §10 (`invoices`), and §3 (`documents`) directly, scoped to `(company_id, customer_id)` from the caller's token — never a client-supplied filter. Response shapes are deliberately whitelisted at the Pydantic layer (`PortalOrderOut`/`PortalQuoteOut`/etc.), never a raw `model_validate()` of the staff-facing schemas: `orders.total_internal_cost`/`total_profit` and `sales_quotes.total_internal_cost`/`total_profit`/`profit_margin_pct`/`internal_notes` (real COGS/margin data) are never returned to a customer. `sales_quotes`/`invoices` rows with `status = 'draft'` are excluded from every customer-facing query entirely (`404` on direct fetch by id) — a customer never sees an internal working copy before staff sends it.

## 16. Unbuilt Modules (conceptual only)

Every module named in the original 10-module roadmap has now shipped (`PROJECT_AUDIT.md` §3; Purchasing in Version 2.31.0, Marketing in Version 2.32.0). Nothing remains in this section — kept as a placeholder heading so downstream section numbers below don't shift again if a genuinely new module is proposed later.

## 17. Row-Level Security Strategy

**Correction from the previous revision of this document: Postgres Row-Level Security is not implemented anywhere in this codebase today.** A grep across all of `backend/` for `ROW LEVEL SECURITY`/`CREATE POLICY`/`row_level_security` returns zero hits — no migration, no raw SQL, nothing (`PROJECT_AUDIT.md` S1). The previous revision described RLS as already-in-place defense-in-depth; that was the Phase-1 design intention, never actually built.

What **is** real and was verified thoroughly during the `PROJECT_AUDIT.md` review: every `get`/`get_by_id`/`list` repository method across every module consistently filters by `company_id` in its `WHERE` clause at the application layer — this is the entire tenant-isolation mechanism running in production today, not a defense-in-depth second layer behind RLS.

The originally-intended design remains a reasonable future hardening step:

```sql
ALTER TABLE crm_customers ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON crm_customers
  USING (company_id = current_setting('app.current_company_id')::uuid);
```

— the backend would need to `SET LOCAL app.current_company_id` at the start of each request's DB transaction (derived from the authenticated user's active company, never client-supplied) for this to function. Not built; recorded here as a real, open gap rather than implied-complete.

## 18. Migration Strategy

- Alembic revision history is a single linear chain (currently 22 migrations deep, head `67e0a8a55a5a` — `stone_fabrication_workflow_phase1`, Version 2.34.0) — unified at the database level, but each module owns the migration scripts that create/alter its own tables.
- Core platform tables (`companies`, `users`, `user_company_roles`, `documents`, `audit_log`, `event_log`, `ai_jobs`) were created in the earliest migration, before any module's tables.
- **Correction from the previous revision of this document**: there is no CI step that runs `alembic upgrade head` against a disposable database on every PR — that claim was aspirational, not built. What actually runs today: the test suite (`pytest`, wired into `.github/workflows/ci.yml` as of Version 2.28.0) builds its schema via SQLAlchemy's `Base.metadata.create_all()` directly from the current model definitions, entirely bypassing the Alembic migration chain — so a passing test suite does not, by itself, prove the migration chain is consistent with the models. `alembic check` (run manually, most recently confirmed clean during the Version 2.28.0 audit pass) is the actual verification that the migration chain matches the models; it is not yet part of the CI workflow. A real gap worth closing in a future pass, not claimed as already closed here.
- Module removal does not auto-drop tables; a deliberate downgrade migration is required if data removal is intended.
