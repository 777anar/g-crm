# Changelog

All notable changes to this project are documented in this file. See [ROADMAP.md](ROADMAP.md) for full delivery narratives, rationale, and what's next; this file is the terse, dated summary.

## [2.35.0] — 2026-07-22 — Stone Fabrication Workflow, Phase 2 (Cut Optimization & Smart Offcut Management)

Builds directly on Phase 1's slab lifecycle and offcut tracking: a slab could already become `offcut_created` and register a remnant, but nothing computed *how* a piece would actually fit on a slab, ranked which remnant was the best candidate for a job, or gave anyone a picture of the shop floor's queues at a glance. This phase closes all three, plus the two supporting capabilities (a browsable Offcut Library, a queryable Optimization History) that Smart Offcut Management needs to be more than a one-off calculation.

### Added
- **Cut Optimization engine** — a new `cut_optimization` module (`depends_on=["catalog"]`) with a pure, framework-free shelf/guillotine nesting algorithm (`modules/cut_optimization/domain/cutting_algorithm.py`): largest-piece-first placement, best-fit-decreasing-width tie-break within a shelf, rotation tried when allowed, kerf (blade width) subtracted as real lost area between pieces and between shelves — not just between pieces. `POST /cut_optimization/runs` accepts either a real `slab_id` (a Catalog slab or offcut) or hypothetical `slab_length_mm`/`slab_width_mm`, and returns per-piece placements (`x_mm`/`y_mm`/`length_mm`/`width_mm`/`rotated`) in real millimeter coordinates, unplaced pieces with a reason, and `utilization_pct`/`waste_area_m2`/`placed_area_m2`/`total_area_m2`.
- **Smart Offcut Management** — `POST /cut_optimization/recommendations`: given a material (+ optional thickness/finish/warehouse) and a piece list, searches every `available` offcut, runs the same nesting algorithm against each as a candidate, and ranks the ones that fit by utilization descending (least waste first). Returns a human-readable explanation per candidate (e.g. "Selected SL-042: fits all requested pieces at 87.50% utilization…") and `recommend_new_slab: true` with a reason only when nothing in stock can fit the requirement — a new slab purchase is never suggested while a usable offcut exists. The winning candidate is automatically persisted as Optimization History.
- **Offcut Library** — `GET /catalog/slabs/offcuts`, a dedicated search over existing `catalog_slabs` (no new table: an offcut is a completely normal slab, and a parallel table would just be a second source of truth for the same physical piece) filterable by material, thickness/finish (joined from Material), warehouse, minimum length/width/area, and slab number. `catalog_slabs` gained an optional `image_document_id` (same single-placeholder-image pattern as `catalog_brands.logo_document_id`; the frontend shows a generic placeholder graphic when unset — no upload flow was built for it this phase).
- **Optimization History** — every run (manual or the winning offcut recommendation) is persisted to a new `cut_optimization_runs` table as an immutable snapshot (`GET /cut_optimization/runs` list, `GET /cut_optimization/runs/{id}` reopen) — reopening a past layout is a plain read, never a recompute.
- **Production Planning Dashboard** — `GET /reports/production-planning` (Reports module, which gained `"production"` in its `depends_on`): every non-terminal work order grouped by its configurable Phase-1 stage (CNC/Waterjet/Cutting/Polishing/Quality Control/etc., lazily seeded exactly like `GET /production/stages`), enriched with customer/order name, priority, assigned operator, and a server-computed `is_overdue` flag, plus workload counts per operator. A live snapshot, not date-ranged, same convention as Inventory Analytics.
- **Frontend**: a new `/cut-optimization` tool (custom-dimensions or existing-slab/offcut input, a repeatable piece-list editor, kerf/rotation controls) rendering the result as a real-millimeter-coordinate SVG via `viewBox` — no manual pixel-scaling math, fully responsive; `/cut-optimization/recommendations` (Smart Offcut search UI, ranked candidate cards with the same SVG visualization); `/cut-optimization/history` (list) and `/cut-optimization/history/[id]` (reopen); `/catalog/offcuts` (Offcut Library browse/search with placeholder-image cards); `/reports/production-planning` (a new "Production Planning" tab on the existing Reports layout — a true Kanban-by-stage board with overdue jobs highlighted red and an operator-workload bar list). All four reachable from an extended "Production" settings group.
- 35 new backend tests: 10 pure algorithm unit tests (piece placement, kerf spacing, rotation, unplaced-piece reporting, multi-shelf stacking, quantity expansion, 100% utilization), plus API tests for run creation (real slab and hypothetical dimensions), history list/reopen/company-isolation, recommendation ranking (including a deliberate "tight-fit offcut ranks above a loose-fit one" case and material/thickness/finish filtering), Offcut Library search filters, and Production Planning Dashboard grouping/overdue/workload — see `backend/tests/cut_optimization/`, `backend/tests/catalog/test_offcut_library.py`, `backend/tests/reports/test_production_planning.py`.
- A real Alembic migration (`98b251470b25_cut_optimization_phase2.py`), generated via `alembic revision --autogenerate`, applied to and verified against the actual dev database (`alembic check` clean) — adds `cut_optimization_runs` and `catalog_slabs.image_document_id`, with `batch_alter_table` for the new FK constraint (SQLite can't `ALTER` a constraint directly, same pattern as Phase 1's migration).
- A live end-to-end smoke test against the running app and dev database (raw-dimension run → real-slab run → history list/reopen → recommendation with zero offcuts correctly suggesting a new slab → an offcut registered and then correctly recommended, ranked, and explained → Offcut Library search → Production Planning Dashboard), plus a full Playwright pass over the actual rendered frontend (the tool page, a completed run's SVG layout, history reopen, the Offcut Library grid, the Production Planning board, and a live recommendation search) with zero console/runtime errors.

### Fixed
- A tab-highlighting bug caught during this pass' own Playwright smoke test (not present before this feature): the Reports layout's active-tab check used a plain prefix match, so adding the new "Production Planning" tab (`/reports/production-planning`) made the pre-existing "Production Analytics" tab (`/reports/production`) highlight simultaneously, since one href is a string-prefix of the other. Fixed with an exact-or-trailing-slash boundary check.

### Documentation
`API_SPECIFICATION.md` §11 (Offcut Library), §17 (Production Planning), and new §23 (Cut Optimization module); `DATABASE_DESIGN.md` §5.6/§8.6 and new §16 (repurposing the "Unbuilt Modules" placeholder heading explicitly held open for exactly this situation) document the full contract.

### Verification
Full backend suite passing (695/695 — 660 prior + 35 new), `lint-imports` passing (1 contract kept, 0 broken), frontend `tsc --noEmit` clean, frontend production build clean (6 new routes), i18n key parity verified across az/ru/en (1538 keys each).

## [2.34.0] — 2026-07-22 — Stone Fabrication Workflow, Phase 1 (Material Reservation, Slab Lifecycle, Configurable Production Stages)

The first release built specifically for the stone/slab fabrication business rather than as a generic ERP capability — closes real gaps found by direct code review: assigning a slab to a quote item never actually reserved it (double-booking was possible up until quote acceptance), a slab's own lifecycle had no concept of "just delivered but not yet shelved" or "cut with a usable remnant," and Production's shop-floor stages were a fixed 6-value enum with no priority, no assigned operator, and no timeline. All changes are additive to existing, already-shipped behavior: no existing status value, transition, or API response field was renamed or removed.

### Added
- **Material Reservation** — a new `catalog_slab_reservations` table (Catalog module) is the durable, queryable record of "this slab is allocated to this order item," distinct from `catalog_slabs.status` (which only tells you a slab *is* reserved, never for whom). `POST /catalog/slabs/{id}/reserve` reserves a slab for an order item (idempotent for the same item; `409` if another item already holds an active reservation — the double-booking guard); `POST /catalog/slabs/reservations/{id}/release` and `GET /catalog/reservations?order_id=` round out the surface. Orders' `CreateOrderUseCase` now backfills a reservation row for every slab-linked item copied from an accepted quote (the slab was already moved to `reserved` by Sales at quote-acceptance time — adoption records the formal reservation without re-validating availability), giving 100% reservation coverage with zero changes to the Sales module.
- **Full slab lifecycle** — `catalog_slabs.status` gains three new values, additive to the original five: `received` (Purchasing's receiving flow now creates slabs in this status instead of jumping straight to `available` — an explicit "shelve to stock" `PATCH .../status` is required before a received slab can be reserved), `offcut_created` and `consumed` (a work order's completion now moves its slabs to `consumed`, not `sold` — `sold` remains valid for any non-fabrication direct-sale flow). New `POST /catalog/slabs/{id}/offcuts` registers a remnant piece cut from an `in_production` slab as its own independently reservable `Slab` row (`is_offcut`, `parent_slab_id`) and moves the parent to `offcut_created`.
- **Configurable Production Stages** — a new per-company `production_stages` table (Measuring, Design, CNC, Waterjet, Cutting, Polishing, Quality Control, Ready for Installation seeded by default, freely renamable/reorderable/hideable via `GET/POST /production/stages`, `PATCH /production/stages/{id}`), and `work_orders.current_stage_id` tracks a job's position in that pipeline — independent of, and not gated by, the pre-existing coarse status lifecycle (`queued→cutting→...→completed`), which is unchanged and still drives the Order/slab cascades.
- **Production Job enrichment** — `work_orders` gains `priority` (`low`/`normal`/`high`/`urgent`, settable at creation and via `POST /production/{id}/priority`) and operator assignment (`POST /production/{id}/assign`, validated against company membership). A new `GET /production/{id}/job` endpoint assembles the full "Production Job" view in one call: customer, project, order, priority, due date, assigned operator, current stage, and every reserved slab enriched with material name/thickness/finish.
- **Production timeline** — a new `work_order_events` table records every status/stage/priority/operator change on a job (`GET /production/{id}/timeline`), human-readable and chronologically ordered, sitting alongside (not replacing) the standard `core.audit_log` entry every one of these writes already records.
- **Frontend**: Production's list page gained Priority and Due Date columns; the work order detail page (`/production/[id]`) was rewritten into the full Production Job view — customer/project links, an editable priority/operator/stage/due-date/notes panel, a Material/Thickness/Finish-enriched slabs table, and the timeline. New `/production/stages` settings page (add/rename/hide stages), reachable from a new "Production" group on `/settings`.
- 30 new backend tests (`tests/catalog/test_slab_reservations.py`, `tests/production/test_stages.py`, `tests/production/test_work_order_tracking.py`, plus one in `tests/orders/test_orders.py`): reservation create/idempotent-reuse/double-booking-conflict/release, the `received`→`available` gate, offcut creation (requires `in_production`, rejects otherwise), multi-company isolation for both reservations and stages, stage seeding/CRUD, priority/operator/stage tracking mutations (incl. operator-not-in-company validation), timeline ordering, and full work-order-lifecycle assertions updated for the `consumed` (not `sold`) completion target.
- A real Alembic migration (`67e0a8a55a5a_stone_fabrication_workflow_phase1.py`), generated via `alembic revision --autogenerate`, applied to and verified against the actual dev database (`alembic check` clean) — adds `catalog_slab_reservations`, `production_stages`, `work_order_events`, and the new columns on `catalog_slabs`/`work_orders`, with `batch_alter_table` for the two new FK constraints (SQLite can't `ALTER` a constraint directly).
- A live end-to-end smoke test against the running app and dev database (not just the automated suite): received → shelved → reserved (blocked while `received`, blocked on double-booking) → order created (reservation adopted) → work order created (priority/due date) → stage/operator/priority updates → full status lifecycle to `completed` (slab → `consumed`, reservation → `consumed`) → a second slab driven to an offcut. Confirmed working end-to-end before this was considered done, plus a Playwright pass over the actual rendered frontend pages (list, stages, job detail) with zero console/runtime errors.

### Fixed
- A router-composition bug caught during this pass' own smoke test (not present before this feature): merging Production's new `stages`/`job` routers via `include_router()` put the pre-existing catch-all `GET /{work_order_id}` ahead of the new literal `GET /stages` route in resolution order, so `GET /production/stages` would have been silently swallowed by the work-order-by-id route. Fixed by splicing the more specific routers' routes ahead of the catch-all instead of appending.

### Documentation
`API_SPECIFICATION.md` §11/§14/§14a and `DATABASE_DESIGN.md` §5.6/§5.6a/§8 document the full endpoint/schema contract.

### Verification
Full backend suite passing (660/660 — 630 prior + 30 new), `lint-imports` passing (1 contract kept, 0 broken), frontend `tsc --noEmit` clean, frontend production build clean (56 routes — 1 new, `/production/stages`), i18n key parity verified across az/ru/en (1457 keys each).

## [2.33.0] — 2026-07-21 — Customer Portal

The first module built beyond the original ten-module plan (`PROJECT_ANALYSIS.md` §2), same category as Communication Center. Closes a real gap: every screen in this application was staff-facing, so a G-STONE customer checking their order status, quote, invoice balance, or installation date had to call the office. Fundamentally different from every prior module: it needs a second, entirely separate authentication identity, since a customer is not a member of any company's staff RBAC hierarchy. Built as a full Clean Architecture module (`modules/customer_portal/{domain,application,infrastructure,presentation}`) with `depends_on=["crm", "sales", "orders", "finance", "installation"]` — `customer_portal_logins` carries a real FK to `crm_customers.id` (safe here, unlike Marketing's `campaign_id`, because this table lives in the *dependent* module), and the customer-facing read endpoints query Order/Quote/Invoice/InstallationJob directly, the same "depends_on for read access" pattern Reports and Marketing use.

### Added
- **Customer login identity** — `customer_portal_logins` table (1:1 with `crm_customers`, real FK). JWTs carry a distinct `"type": "customer_access"`/`"customer_refresh"` claim (vs. staff's `"access"`/`"refresh"`) and only `customer_id`/`company_id` — no role, no permissions. `get_current_customer` (customer_portal's own dependency) and `core.rbac.dependencies.get_current_user` (staff) each reject the other's token type, confirmed by tests exercising both directions plus a live smoke test against the running app. Reuses only the low-level primitives from staff auth: `hash_password`/`verify_password`, the JWT encode/decode pattern, and `core.auth.token_denylist` (keyed by the customer login's own id) for refresh-token revocation.
- **Staff-side access management** (`/customer_portal/admin/...`, `customer_portal:access:{read,write}` permissions) — enable portal access (`POST .../access`, body `{email, password}`, `409` on a duplicate customer or email), reset password (`POST .../access/reset-password`), enable/disable (`POST .../access/status`). Every write records an audit entry and publishes a domain event (`CustomerPortalAccessEnabled`/`PasswordReset`/`StatusChanged`), same discipline as every other module.
- **Customer-facing auth** (`/customer_portal/auth/...`, no staff bearer token accepted) — login (rate-limited to 10/minute/IP, a separate bucket from staff login so the two never throttle each other), refresh, logout-everywhere. Mirrors `core/auth/service.py`'s login/refresh/logout functions almost exactly, scoped to `CustomerLogin` instead of `User`.
- **Customer-facing read surface** (`/customer_portal/me/...`, `get_current_customer`) — profile, orders, quotes, invoices, installation jobs, documents, every list cursor-paginated and every query hard-scoped to `(company_id, customer_id)` from the caller's own token, never a client-supplied filter. Every response is a deliberately whitelisted Pydantic schema (`PortalOrderOut`/`PortalQuoteOut`/etc.), never a raw `model_validate()` of the staff-facing schema: `total_internal_cost`/`total_profit`/`profit_margin_pct`/`internal_notes` and other internal-only fields are never returned. `draft` quotes and invoices are excluded entirely (`404` on direct fetch) — a customer never sees an internal working copy before staff sends it. Documents are limited to the customer's own CRM attachments and their own installation-job photos; every other document type is excluded even if it happens to reference an id the customer owns.
- **Frontend**: a "Customer Portal" card on the Customer detail page (`/crm/customers/{id}`) for staff to enable/disable/reset access. A separate, unauthenticated-from-the-staff-app-'s-perspective `/portal/...` route tree with its own login page, session storage (`lib/portal-session.ts`, distinct localStorage keys from staff), API client (`lib/portal-api-client.ts`, its own token-refresh flow), and pages: dashboard, orders (list/detail), quotes (list/detail), invoices (list/detail), installation (list), documents (list + download).
- 31 new backend tests (`tests/customer_portal/`): access-management CRUD + permission/conflict/not-found cases, login/refresh/logout including two deliberate cross-token tests (a staff token rejected by `/me`, a portal token rejected by a staff endpoint), and the full customer-facing read surface including ownership enforcement (another customer's order returns `404`, not their data), draft-hiding for quotes/invoices, and document visibility/exclusion.
- A real Alembic migration (`2b84b718b162_customer_portal_module_tables.py`), generated via `alembic revision --autogenerate`, applied to and verified against the actual dev database (`alembic check` clean) — confirmed to add only `customer_portal_logins`, no other schema changes.
- A live end-to-end smoke test against the running app and dev database (not just the automated suite): enable portal access for a real customer → customer login → `/me`/`/me/orders` read → a staff token rejected on `/me` → a portal token rejected on a staff endpoint, all confirmed working before this was considered done.

### Documentation
`API_SPECIFICATION.md` §22 and `DATABASE_DESIGN.md` §15 document the full endpoint/schema contract; `README.md` and `ROADMAP.md` updated to reflect thirteen shipped modules.

### Verification
Full backend suite passing (630/630 — 599 prior + 31 new), `lint-imports` passing (1 contract kept, 0 broken), frontend `tsc --noEmit` clean, frontend production build clean (55 routes — 10 new), i18n key parity verified across az/ru/en (1414 keys each).

## [2.32.0] — 2026-07-21 — Marketing Module

The last of the ten modules on the original plan (`PROJECT_ANALYSIS.md` §2). Closes a real gap: `crm_leads.campaign` and `crm_customers.advertising_campaign` were free-text fields with no aggregation behind them — there was no real answer to "which campaign brought in this lead" or "did this campaign make money." Built as a full Clean Architecture module (`modules/marketing/{domain,application,infrastructure,presentation}`) with `depends_on=["crm", "orders"]` for read-only cross-module attribution queries — the same "depends_on for read access" pattern Reports uses against every other module. CRM itself gained no dependency on Marketing: `crm_leads.campaign_id` is an unconstrained, indexed, nullable UUID column with no DB-level FK, the same "polymorphic reference, application-layer only" pattern already used by `documents.related_entity_id` and `crm_activities.related_entity_id`.

### Added
- **Campaigns** — `campaigns` table: `name`, `channel` (same vocabulary as CRM lead `source_channel`), `budget`/`currency`, `start_date`/`end_date`, `notes`, a `draft→active→{completed,cancelled}` status lifecycle. `GET/POST /marketing/campaigns`, `GET/PATCH /marketing/campaigns/{id}` (blocked once terminal), `POST /marketing/campaigns/{id}/status` (`422` on an invalid transition).
- **Lead attribution** — `crm_leads` gains `campaign_id` (nullable UUID, indexed, no FK). `CreateLeadInput`/`LeadCreate`/`LeadOut` all extended additively; existing leads and the pre-existing free-text `campaign` field are untouched.
- **Performance** — `GET /marketing/campaigns/{id}/performance`, computed live via `CampaignPerformanceRepository` (not a stored/cached value): `leads_count` (CRM leads carrying this campaign's id), `converted_count` (of those, how many converted to a customer), `conversion_rate`, and `attributed_revenue` (sum of `total_final` across converted customers' orders, counting only revenue-bearing statuses `ready`/`delivered`/`installed`/`completed` — a cancelled order never inflates a campaign's apparent ROI). Verified company-scoped, not just campaign-id-scoped, via a deliberate cross-tenant `campaign_id` collision test.
- **Frontend**: the Lead capture form (`/crm/leads`) gained a live campaign picker (active campaigns only) alongside the pre-existing free-text field. `/marketing/campaigns` (list + inline create, cursor-paginated), `/marketing/campaigns/[id]` (live performance stat cards, status actions, draft/active-only budget/notes editing). Reachable from the `/settings` hub (new "Marketinq"/"Маркетинг"/"Marketing" group).
- 16 new backend tests (`tests/marketing/`): campaign CRUD + permission/search/pagination, the full status transition graph, update-blocked-when-terminal, performance with no leads (all zeros), performance with a mix of converted/unconverted leads (conversion rate), performance ignoring cancelled orders, multi-company isolation (including the cross-tenant `campaign_id` collision case), and audit-log + domain-event coverage for campaign creation and status changes.
- A real Alembic migration (`430944e10164_marketing_module_tables_and_crm_leads_.py`), generated via `alembic revision --autogenerate`, applied to and verified against the actual dev database (`alembic check` clean) — confirmed to add `crm_leads.campaign_id` with no FK constraint, as designed.

### Fixed
- `tests/purchasing/` and `tests/marketing/` were both missing `__init__.py` (present in every other module's test package), which caused a pytest module-name collision between the two packages' identically-named `test_isolation_and_events.py` files the moment both existed. Added both files, matching the established pattern.

### Documentation
`API_SPECIFICATION.md` §21 and `DATABASE_DESIGN.md` §14 document the full endpoint/schema contract; `README.md` and `ROADMAP.md` updated to reflect all twelve shipped modules — the original ten-module plan is now complete.

### Verification
Full backend suite passing (599/599 — 583 prior + 16 new), `lint-imports` passing (1 contract kept, 0 broken), frontend `tsc --noEmit` clean, frontend production build clean (45 routes — 2 new), i18n key parity verified across az/ru/en (1338 keys each).

## [2.31.0] — 2026-07-21 — Purchasing Module

The first new business module since Version 2.9 (Real Integrations), and the first of the two remaining modules from the original ten-module plan (`PROJECT_ANALYSIS.md` §2 — Marketing is now the only one left). Closes a real gap: until now there was no system of record for who G-STONE buys stone from, what's on order, or when a purchase order's receipt actually becomes sellable inventory — restocking was entirely untracked outside spreadsheets. Built as a full Clean Architecture module (`modules/purchasing/{domain,application,infrastructure,presentation}`), following the exact same manifest/permissions/navigation contract every other module uses — `core/` required zero changes beyond the one-line `INSTALLED_MODULES` addition the plugin architecture promises.

### Added
- **Suppliers** — `suppliers` table, full CRUD with `active`/`hidden` status (the same lightweight-entity pattern as Catalog Brands/Warehouses): `GET/POST /purchasing/suppliers`, `GET/PATCH /purchasing/suppliers/{id}`, cursor-paginated list with search.
- **Purchase Orders** — `purchase_orders` + `purchase_order_lines` tables. Created against an active Supplier with one or more line items (each optionally linked to a `catalog_materials` row, or a free-text non-material cost like freight): `POST /purchasing/purchase-orders`. A `draft→sent→confirmed→{partially_received,received}/cancelled` status lifecycle — only `sent`/`confirmed`/`cancelled` are manually settable via `POST /purchase-orders/{id}/status`; `partially_received`/`received` are set exclusively as a side effect of receiving, the same discipline Finance's `invoice.status` already uses for `partially_paid`/`paid`. Only a `draft` order's notes/expected-delivery-date may still change (`PATCH /purchase-orders/{id}`) — lines are fixed at creation, the same accepted tradeoff this codebase already lives with for Quote Sections.
- **Receiving** — `goods_receipts` table. `POST /purchase-orders/{id}/lines/{line_id}/receive` accumulates `quantity_received` on a line (capped at the line's ordered `quantity`) and, when given a warehouse + slab number, creates a **real `catalog_slabs` row** in the same call by reusing Catalog's own `CreateSlabUseCase` — the exact cross-module-reuse pattern Production already uses for slab status changes (`UpdateSlabStatusUseCase`), now applied to the inverse (restocking) flow instead of consumption. `GET /purchase-orders/{id}/receipts` lists the full receiving history.
- **Frontend**: `/purchasing/suppliers` (list + inline create, cursor-paginated), `/purchasing/orders` (list, status filter, cursor-paginated), `/purchasing/orders/new` (supplier picker + repeatable line-item rows with a Catalog material dropdown, live-computed estimated total), `/purchasing/orders/[id]` (status actions, draft-only notes/delivery-date editing, per-line inline receiving form, receipt history table). Reachable from the `/settings` hub (new "Təchizat"/"Снабжение"/"Purchasing" group) and via the existing secondary-route title-matching in `AppShell`.
- 24 new backend tests (`tests/purchasing/`): Supplier CRUD + permission/search/pagination, Purchase Order creation (totals computation, empty-lines/inactive-supplier rejection), the full status transition graph (including the "not manually settable" and "illegal transition" cases), receiving (full receipt creates a slab and marks the order `received`; partial receipt marks `partially_received`; over-receiving, receiving against a non-receivable order, and receiving with slab details against a material-less line are all rejected), multi-company isolation, PO-number-sequence-per-company reuse, and audit-log + domain-event coverage for every write action.
- A real Alembic migration (`4c0488d40756_purchasing_module_tables.py`), generated via `alembic revision --autogenerate`, applied to and verified against the actual dev database (`alembic check` clean) — not hand-written, avoiding the exact "shipped with no migration" bug an earlier session found and fixed for the Orders module.

### Documentation
`API_SPECIFICATION.md` §20 and `DATABASE_DESIGN.md` §13 document the full endpoint/schema contract; `README.md` and `ROADMAP.md` updated to reflect eleven shipped modules (Marketing is the only one remaining from the original plan).

### Verification
Full backend suite passing (583/583 — 559 prior + 24 new), `lint-imports` passing (1 contract kept, 0 broken), frontend `tsc --noEmit` clean, frontend production build clean (42 routes — 4 new).

## [2.30.0] — 2026-07-21 — Fix: Orders/Production/Installation/Finance List Endpoints Never Actually Paginated

Found during the Version 2.29.0 documentation sync and fixed immediately as the highest-value follow-up: `GET /orders`, `GET /production`, `GET /installation/jobs`, `GET /finance/invoices`, and `GET /finance/expenses` all accepted `limit`/`cursor` query parameters and forwarded them to their repository's `LIMIT`/`OFFSET` query, but every one of them hardcoded `next_cursor=None` in the response regardless of whether more rows existed. This silently undermined the "Load more" UI added for Orders, Production, and Finance in Version 2.26.0 — the button can only ever appear when the backend returns a real cursor, so those pages were still effectively capped at one page (25–200 rows depending on the endpoint) despite being reported as fixed. Catalog Brands, Materials, and Slabs, CRM Customers/Leads/Tasks, and Communication/AI endpoints were never affected — they already used the correct pattern this fix brings the other five in line with.

### Fixed
- All five endpoints now fetch `limit + 1` rows, detect whether a row past the requested page exists, and return a real `encode_cursor(...)`-produced `next_cursor` when it does — the exact pattern already proven correct on `catalog:materials`/`catalog:brands`/`crm:customers`/`crm:leads`. No response schema change, no frontend change required — the "Load more" buttons added in 2.26.0 for Orders/Production/Finance now actually function past page one, and Installation Jobs (which had no frontend pagination UI yet) is ready for it whenever that's built.
- 5 new backend tests (`test_orders_cursor_reaches_the_next_page`, `test_work_orders_cursor_reaches_the_next_page`, `test_installation_jobs_cursor_reaches_the_next_page`, `test_invoices_cursor_reaches_the_next_page`, `test_expenses_cursor_reaches_the_next_page`) — each creates 3 records, requests a page of 2, and confirms a non-null cursor reaches a real, disjoint second page.

### Verification
Full backend suite passing (559/559 — 554 prior + 5 new), `lint-imports` passing, frontend `tsc --noEmit` clean, frontend production build clean (39 routes, unchanged — no frontend files touched).

## [2.29.0] — 2026-07-21 — Documentation Sync: API_SPECIFICATION.md & DATABASE_DESIGN.md (PROJECT_AUDIT.md Priority #4)

Closes `PROJECT_AUDIT.md`'s Priority #4/#9 finding: `API_SPECIFICATION.md` and `DATABASE_DESIGN.md` had drifted badly — both stopped documenting real endpoints/schema after Version 2.12, and worse, their CRM and Sales sections still described the original **Phase-1 design sketch** (generic Contact/Account/Deal/Pipeline-Stage CRM, a flat Quote/SalesOrder Sales model) that was never actually built that way once real requirements arrived. Production, Installation, and Finance — three fully-shipped, tested modules — were still listed as "conceptual, not migrated." Both documents were rewritten from scratch against the actual current source (every FastAPI router and SQLAlchemy model in `backend/`, verified file-by-file, not carried forward from the previous doc text), plus `README.md` and `ROADMAP.md` brought current through Version 2.28.0. Documentation-only; no application behavior changed.

### Changed
- **`API_SPECIFICATION.md`**: full rewrite, renumbered into a clean per-module structure (Core/shared endpoints §7–9, then one section per module §10–19, then Rate Limiting/Mobile Parity). Replaced the fictional CRM Contacts/Accounts/Deals/Pipeline-Stages endpoints with the real Customers/Leads/Tasks/Task-Notifications surface; replaced the fictional flat Sales Quotes/Orders with the real nested Sales tree (Projects → Quotes → Sections → Items/Measurements, and the parallel Project workspace: Rooms → Project Items → Measurements/Drawings/Photos) and a separate Orders module section. Added full first-time coverage for Production, Installation, Finance, and Reports (previously undocumented entirely). Corrected several drifted claims found during verification: `POST /auth/logout` now correctly documents its `{refresh_token}` body and logout-everywhere behavior (2.22.0); `GET /catalog/brands` now shows its cursor pagination (2.26.0); the events-log endpoint's actual owner-only role check (not a registered permission) and missing `company_id` param; the file-upload endpoint's actual fixed permission (not "varies by module") and its 10 MB size cap / content-type allowlist; a previously-undocumented `next_cursor` gap on Orders/Production/Installation/Finance list endpoints (always `null` despite accepting `limit`/`cursor`); a previously-undocumented `GET /core/companies/users` endpoint backing every "assign to a user" picker in the app; and a correction that no endpoint anywhere uses the originally-planned `202 Accepted` async job-polling pattern — every current endpoint, including AI analysis, is synchronous.
- **`DATABASE_DESIGN.md`**: full rewrite, renumbered by module (§3 Core, §4 CRM, §5 Catalog, §6 Sales, §7 Orders, §8 Production, §9 Installation, §10 Finance, §11 Communication, §12 AI, §13 unbuilt modules). Replaced the fictional `contacts`/`accounts`/`deals`/`pipeline_stages`/`quotes`/`sales_orders` schema with the real `crm_customers`/`crm_contacts`/`crm_leads`/`crm_tasks` and `sales_quotes`/`sales_projects`/`orders` tables (confirming, among other things, that pipeline stages are a hardcoded Python list, not a per-company-configurable table, and that Orders is a fully separate module from Sales with its own deep-copied tables, not `sales_orders`). Added full first-time coverage of Production, Installation, and Finance's real tables. Corrected several drifted claims: `ai_jobs` (core) is confirmed unused in production — the AI module writes exclusively to its own `ai_recommendations` table instead; refresh-token revocation (2.22.0) lives entirely in Redis/in-memory, not a database column; Row-Level Security (previously documented as implemented defense-in-depth) is confirmed **not implemented anywhere** in the codebase — application-layer `company_id` filtering is the actual, sole tenant-isolation mechanism running today; and the migration-strategy section's claim that CI runs `alembic upgrade head` was corrected — the test suite builds its schema via `Base.metadata.create_all()` directly from the models, bypassing the migration chain entirely, so a passing test suite doesn't by itself prove migration/model consistency. Also documented the real `crm_customers`↔`crm_contacts` circular FK (`PROJECT_AUDIT.md` B5) and the confirmed-real composite indexes from migration `e042f8386f09`.
- **`README.md`**: Status section extended from Version 2.18.0 through 2.28.0 (ten entries had never been added); doc list at the top now notes `PROJECT_AUDIT.md` and that the API/DB docs are kept in sync with real source.
- **`ROADMAP.md`**: added the missing "## Version 2.24.0" through "## Version 2.28.0" narrative sections (the Summary table already covered them; the per-version narrative sections did not), and replaced the stale "CRM Version 1.0 is frozen, no new features until approved" header with a status line reflecting the current version.

### Verification
Documentation-only change — no code, tests, or build artifacts touched. Full backend suite unaffected (554/554, last verified in Version 2.28.0); frontend `tsc --noEmit`/`next build` unaffected. Verification for this pass consisted of cross-checking every documented endpoint/table against its router/model source file directly (via four independent extraction passes covering CRM/Sales/Orders and Production/Installation/Finance/Reports, on both the API and schema side), not against the previous revision of either document.

## [2.28.0] — 2026-07-21 — Real CI Enforcement of the Core/Module Architecture Boundary (PROJECT_AUDIT.md Priority #3)

Closes `PROJECT_AUDIT.md` §5/§8/§9 (S2): `PROJECT_ANALYSIS.md` sections 4.3/7/10 have always described the core→module import boundary as "enforced by a CI lint rule... not just a convention," and `pyproject.toml` has declared an `import-linter` contract since Phase 1 — but `import-linter` was never actually installed (missing from `requirements.txt`, failed to even run), and no CI pipeline existed in this repository at all. The only thing actually stopping a violation was `tests/test_core_independence.py`, which only ran when someone remembered to run `pytest` locally. This closes that gap for real: `import-linter` runs, and now nothing merges without both it and the full backend/frontend check suite passing.

### Added
- `.github/workflows/ci.yml` — GitHub Actions workflow on every push/PR to `main`, two jobs: **backend** (`pip install -r requirements.txt`, `pytest`, `lint-imports`) and **frontend** (`npm ci`, `npm run typecheck`, `npm run build`). Any failing step fails the job and blocks the pipeline — this is the CI-enforced architecture gate `PROJECT_ANALYSIS.md` has described since Phase 1 but that never actually existed until now.
- `import-linter==2.13` added to `backend/requirements.txt` (previously configured in `pyproject.toml` but not an installable/runnable dependency anywhere).

### Fixed
- `pyproject.toml`'s `[tool.importlinter]` config used `root_package = "core"` with a `forbidden_modules = ["modules"]` contract — since `modules` sits outside the single declared root package, running `lint-imports` errored immediately ("must have `include_external_packages=True`") rather than ever actually evaluating the contract. Changed to `root_packages = ["core", "modules"]` (both are real top-level packages under `backend/`) so the contract runs and evaluates correctly. Verified with a temporary, deliberately-introduced `core -> modules` import: `lint-imports` correctly reported it as broken, then verified clean again after reverting — this contract now has real teeth, not just plausible-looking config.

### Changed
- `backend/README.md`, `CLAUDE.md`: documented `lint-imports` as a real, runnable command alongside `pytest`, and noted both now run automatically in CI.

### Verification
Full backend suite passing (554/554, unchanged — no application code touched), `lint-imports` passing (1 contract kept, 0 broken) and confirmed to correctly fail on a real violation before being reverted, frontend `tsc --noEmit` clean, frontend production build clean (all 39 routes, unchanged).

## [2.27.0] — 2026-07-21 — Dashboard Resilience & Accurate KPI Counts (PROJECT_AUDIT.md Priority #2)

Closes the next-highest finding from `PROJECT_AUDIT.md` §4/§10 (B2/B3): the Dashboard's 11-way parallel fetch was all-or-nothing (one failing call blanked the entire page, including sections that don't depend on it), and several of its stat/KPI counts were computed from collections silently capped at 100 rows with no way to reach the rest. Frontend-only; no backend or API contract changes, no visual change to the page when every call succeeds.

### Fixed
- **Resilience (B2)**: replaced the Dashboard's `Promise.all` fan-out with `Promise.allSettled`. Previously, any single rejected call (e.g. a transient error on Inventory Analytics) meant `.then()` never ran at all, so nothing — not even the unrelated, already-successfully-fetched sections — ever rendered; the page was stuck on the loading skeleton behind a single error line. Each of the 9 calls is now applied independently from its own settled result, defaulting to an empty/`null` value only for the piece that failed. The `loading` gate no longer depends on every individual piece of state being non-null (which could never resolve if one call kept failing) — it now flips once the whole settle batch completes, regardless of outcome.
- **JSX gating**: the KPI/revenue-trend section (which needs `executive` data specifically) is now independently gated from the Inventory snapshot and the "Today" operational sections (tasks, installations, overdue orders, notifications, recent inquiries), which don't depend on it. A failure of the Executive Dashboard call alone no longer hides sections that have nothing to do with it. Markup and layout are unchanged for the successful-load case.
- **KPI under-counting (B3)**: `Orders`, `Production` (work orders), and `Tasks` were fetched with a hardcoded `limit: 100` and no follow-up, so `statOverdueWork`, `statInProduction`, and the overdue-orders list would silently under-count once a company passed 100 rows in any of those collections. Added `lib/fetch-all-pages.ts` — a small, generic `fetchAllPages()` helper that follows a cursor-paginated endpoint's `next_cursor` to completion (capped at 50 pages as a runaway-loop safety valve, not a real-world limit) — and applied it to Orders, Production, and Installation Jobs, the three collections these stats are actually derived from.
- **Recent Inquiries**: previously fetched 100 leads and sorted/sliced to 5 client-side. Now requests exactly `{ sort: "-created_at", limit: 5 }` from the existing `listLeads` endpoint — correct regardless of total lead count, and one fewer bulk fetch.
- **Customer/project name lookups**: previously fetched up to 100 customers and 100 projects in bulk just to build `id -> name` lookup maps for the Overdue Projects and Upcoming Installations sections — itself an uncapped-count risk (a company with >100 customers could see blank names) and wasteful (fetching entire tables just to label a handful of rows). Replaced with targeted per-id lookups (`getCustomer`/`getProject`) for only the customer/project ids actually referenced by the rows being rendered, mirroring the same pattern already used on the Orders and Production list pages.

### Verification
Full backend suite passing (554/554, unchanged — no backend files touched this pass), frontend `tsc --noEmit` clean, frontend production build clean (all 39 routes).

## [2.26.0] — 2026-07-21 — Pagination Rollout (PROJECT_AUDIT.md Priority #1)

Closes the highest-priority finding from `PROJECT_AUDIT.md` §4/§10 (B4/P1): five list pages had no "Load more" UI and no way to reach records past the backend's page-size cap, unlike Customers/Leads/Materials (fixed in 2.19.0). Same established cursor-pagination pattern applied to the remaining pages; no UI redesign, no new components.

### Fixed
- **Orders, Production (work orders), Finance Invoices, Finance Expenses**: these four already had full cursor-pagination support end-to-end in their backend endpoints and `lib/api/*.ts` wrappers — only the page components never consumed `next_cursor` or exposed a "Load more" control. Silent truncation at the backend's page-size default (25) is now fixed frontend-only, no backend or API contract changes.
- **Catalog Brands**: unlike the four above, this one *was* a real backend gap — `GET /api/v1/catalog/brands` never accepted `limit`/`cursor` and `BrandRepository.list()`'s default `limit=50` was silently truncating any company with more than 50 brands, with no contract to reach the rest. Added `limit`/`cursor` query params and a `next_cursor` field to `BrandListOut`, following the exact pattern already established by the Materials and Slabs endpoints in the same module. 1 new backend test (`test_brands_cursor_reaches_the_next_page`).

### Investigated, no change needed
- **Catalog Warehouses, Catalog Price Lists**: re-verified against the current repository code (`WarehouseRepository.list()`, `PriceListRepository.list()`) rather than assumed from `PROJECT_AUDIT.md`'s grouping — neither applies a `LIMIT` at all today, so both already return every row unbounded. There is no truncation bug here, so no "Load more" UI was added; doing so would be pagination theater over an endpoint that already returns everything. Left as-is, consistent with these being genuinely small, per-tenant master-data collections.

### Verification
Full backend suite passing (554/554 — 553 prior + 1 new), frontend `tsc --noEmit` clean, frontend production build clean (all 39 routes, unchanged).

## [2.25.0] — 2026-07-21 — G-STONE ERP Executive: Sales/Inventory/Finance Consolidation (Milestone 2)

The app stops being framed as "a CRM." The primary sidebar collapses from 9 module-level sections to 6: Dashboard, Sales, Inventory, Finance, Reports, Settings. Customers, Leads, Tasks, Projects (Quotes), and Orders — previously two separate primary nav items ("Customers" and "Projects") — merge into one cross-linked "Sales" pipeline; Catalog is relabeled "Inventory" in the nav (its URLs and data model are untouched); Finance is promoted from secondary-only to primary; Production, Installation, and Messages move to secondary-only (still fully reachable, nothing deleted — same regrouping precedent Sprint 2 established for the original 9-section sidebar). The executive Dashboard gains a live Inventory snapshot, backed by a new Inventory Analytics endpoint.

### Added
- `components/sales-section-tabs.tsx` — `SalesSectionTabs`, a shared cross-navigation bar (Customers/Leads/Tasks/Projects/Orders) now rendered identically on all five of those pages, replacing two separate, smaller tab groups.
- Backend: `GET /api/v1/reports/inventory` (Inventory Analytics) — a live stock snapshot (total/available/reserved/in-production/sold slabs, available area in m², materials tracked, materials with zero available stock, active warehouse count, slabs by status, available slabs by warehouse), following the exact same use-case/repository/schema pattern as the existing Sales/Production/Installation/Finance analytics endpoints. Unlike those, it's not date-range filtered — stock status is current state, not a historical aggregate (mirrors how Production Analytics' own order-status snapshot already ignores the date range). Full PDF/Excel export parity with every other report type. 4 new backend tests.
- Frontend: `/reports/inventory` — a new Reports tab (Inventory Analytics) with KPI cards, a slabs-by-status breakdown, and available-stock-by-warehouse chart.
- Dashboard: a new "Inventory" section (Available Slabs + area, Materials Out of Stock, Warehouses), sourced from the new endpoint, so the executive snapshot now covers all four priority domains (Sales, Inventory, Finance, Reports) instead of just Sales/Finance.
- New nav i18n keys (`nav.sales`, `nav.inventory`, `nav.finance`) and Inventory Analytics keys, in all three locale files.
- A second Playwright smoke test (`tests/e2e/dashboard.spec.ts`) covering the new nav consolidation end-to-end (Sales → Inventory → Finance → Reports → Inventory Analytics), plus an Inventory assertion added to the original dashboard test.

### Changed
- `components/app-shell.tsx` — `NAV_ITEMS` reduced to `dashboard`/`sales`/`inventory`/`finance`/`reports`/`settings`; `SECONDARY_ROUTES` gained `customers`'-and-`projects`' former primary-nav routes (still title-matched, just not primary links) plus `production`/`installation`.
- `app/(app)/crm/customers`, `crm/leads`, `crm/tasks`, `orders`, `sales/projects` — all five now render `<SalesSectionTabs />` instead of a bespoke, page-local `SectionTabs` block.
- `app/(app)/reports/layout.tsx` — gained an "Inventory Analytics" tab between Sales and Production.

### Verification
Full backend suite passing (553/553 — 549 prior + 4 new), frontend `tsc --noEmit` clean, frontend production build clean (39 routes, including the new `/reports/inventory`), and both Playwright smoke tests passing end-to-end against a freshly restarted local backend and a fresh production build: dashboard KPIs/trend/inventory/today sections all render, and the full nav walk (Sales → Customers/Leads/Tasks/Projects/Orders tabs all present → Inventory → Finance → Reports → Inventory Analytics with real data) resolves correctly — zero console errors throughout. (The Dashboard's "Inventory" section heading and the sidebar's "Inventory" nav link share the same text by design — both are the correct label for what they are — so the new test scopes its assertion to the heading role rather than plain text to disambiguate them, same as a screen reader's heading-vs-landmark navigation would.)

## [2.24.0] — 2026-07-21 — G-STONE ERP Executive: Premium Executive Dashboard (Milestone 1)

First step of repositioning the app from a CRM into an executive tool the owner can read in under 10 seconds. Rewires `/dashboard` onto the real server-side aggregation endpoint (`GET /api/v1/reports/executive`) that `/reports` already exposed but no other page consumed, and gives it a bigger-scale, Apple/Linear/Stripe-influenced KPI layout. No backend changes; the sidebar/IA consolidation into 7 top-level modules is deferred to a follow-up milestone.

### Added
- `components/dashboard/kpi-card.tsx` — `KpiCard`, a large-headline KPI tile (bigger scale than the existing `StatCard`) with an optional month-over-month delta badge, kept separate from `StatCard` so every other module's list-view stat tiles are unaffected.
- Hero KPI row on `/dashboard` — Revenue, Profit (+ margin hint), Active Customers, Orders Created — sourced from `getExecutiveDashboard({period:"30d"})`.
- Revenue & profit trend chart (`TrendChart`, now with gradient area fill) plus an Orders-by-Status pipeline (`StatusBarList`) on `/dashboard`, mirroring the pairing already proven on `/reports`.
- `TrendChart` gained an additive `areaFill` prop (`components/ui/charts.tsx`), default `false` — opted into on the new Dashboard only, `/reports` unaffected.
- `formatNumber()` in `lib/format.ts` — locale-aware thousands-separator formatting for KPI headline figures (the backend returns raw, currency-less Decimal strings since aggregates can span multiple order currencies).
- New i18n keys `dashboard.vsPreviousMonth` / `dashboard.sectionToday` in all three locale files; KPI/chart labels reuse the existing `reports` namespace instead of duplicating strings.
- A real, checked-in Playwright smoke-test harness — `playwright.config.ts`, `tests/e2e/dashboard.spec.ts`, `@playwright/test` devDependency. None existed in the repo before this (prior "live Playwright smoke test" verifications were run ad hoc); this now runs against the actual production build and a live local backend, logging in as the seeded owner and asserting the new KPI cards, trend chart, and pipeline render with zero console errors.

### Changed
- `/dashboard`'s original operational sections (Today's Tasks, Upcoming Installations, Overdue Orders, Notifications, Recent Inquiries) are unchanged in logic and fully preserved, just visually demoted below the new executive snapshot under a "Today" heading.

### Verification
Full backend suite passing (549/549, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), and the new Playwright smoke test passing end-to-end against a freshly seeded local dev database (login → company selection → KPI cards, revenue/profit trend, orders-by-status pipeline, and the preserved "Today" section all render, zero console errors).

## [2.23.0] — 2026-07-14 — Customer Type Picker

Resolves RELEASE_CHECKLIST.md M2 (`customer.type` "write-only dead weight"), deferred since Phase 1 pending a product decision between reintroducing a picker or dropping the column. This session builds the picker. API contracts kept compatible: `CustomerCreate.type` is unchanged; `CustomerUpdate` gains a new optional `type` field (purely additive — previously silently ignored on PATCH, now actually applied).

### Added
- `type` picker on the Customer creation form (defaults to Individual), replacing a hardcoded `type: "individual"` literal.
- Editable `type` picker on the Customer profile page's "Company" card, matching the Assigned Manager picker's inline-select-with-toast pattern.
- `CustomerUpdate.type` (backend) — optional, validated against the same `VALID_CUSTOMER_TYPES` set `CustomerCreate` already uses; wired through `UpdateCustomerInput` and `UpdateCustomerUseCase`.
- `CUSTOMER_TYPES`/`CustomerType` exports in `lib/types.ts`, mirroring `CUSTOMER_STATUSES`/`CustomerStatus`.
- Reactivated the previously-orphaned `useCustomerTypeLabel()` i18n hook by re-adding `customerType.individual`/`customerType.business` to all three locale files (deleted as dead code in 2.18.0 when no UI used it — now it does).
- 5 new backend tests: invalid `type` rejected (400) on create and update, `type` defaults to `individual` when omitted, successful update, and omitting `type` from an unrelated PATCH leaves it unchanged.

### Verification
Full backend suite passing (549/549 — 544 prior + 5 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), and a live Playwright smoke test (create as Business, profile shows Business, change to Individual with toast confirmation, persists across reload) — zero console errors.

## [2.22.0] — 2026-07-14 — Refresh-Token Revocation

Closes the last open Version 1.1 item (RELEASE_CHECKLIST.md M7): `POST /auth/logout` was a literal no-op since Phase 1, and the frontend never even called it — a leaked refresh token stayed valid for its full 30-day lifetime with no server-side kill switch.

### Added
- `core/auth/token_denylist.py` — refresh-token revocation via a per-user monotonic generation counter (not a per-token or timestamp-based denylist). Every refresh token is stamped with a `gen` claim at issue time; logging out bumps the user's generation; the refresh endpoint rejects any token stamped with a stale generation. One integer per user invalidates every refresh token ever issued to them — genuine "logout everywhere."
- Backed by Redis when reachable (first real use of the previously declared-but-unused `REDIS_URL` setting), with an automatic fallback to a single-process in-memory store if Redis is unreachable, mirroring `core/rbac/rate_limit.py`'s existing tradeoff — login/refresh is never blocked by Redis being down.
- Frontend `logout()` API call (`lib/api/auth.ts`), now actually invoked by `AppShell.handleLogout` with the stored refresh token before clearing local storage and redirecting.
- 7 new backend tests (`tests/test_refresh_token_revocation.py`) plus an autouse conftest fixture resetting the denylist singleton between tests.

### Changed
- `POST /auth/logout` now takes `{refresh_token}` in its body (reusing the existing `RefreshRequest` schema) instead of no body.

### Fixed
- A wall-clock revocation-timestamp cutoff was considered and rejected during implementation: JWT timestamps have only second granularity, so a token issued immediately after a logout (e.g. an instant re-login) could land in the same wall-clock second as the logout and be wrongly rejected. The generation-counter design has no such ambiguity — covered by a dedicated regression test.

### Verification
Full backend suite passing (544/544 — 537 prior + 7 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), and live end-to-end verification against the real dev database and both running servers: a live API sequence (login → refresh succeeds → logout → refresh now 401s → fresh login still succeeds), and a live Playwright test of the actual "Log out" button confirming the old refresh token is provably dead afterward — zero console errors.

## [2.21.0] — 2026-07-14 — Bulk Actions on the Customer List

Closes the next Version 1.1 item per the roadmap's own sequencing (pagination in 2.19.0, filter persistence in 2.20.0, bulk actions here): multi-select archive and multi-select status change for the Customers list. Frontend-only — no new backend endpoint; implemented as N calls to the existing single-Customer `PATCH`/`DELETE` endpoints.

### Added
- Row checkboxes and a header "select all" checkbox on the Customers list (scoped to currently loaded rows).
- Bulk action bar (shown when ≥1 row selected): live selected count, "Clear selection", bulk status change (dropdown + Apply), and a destructive "Archive selected" button gated behind the existing `useConfirm` dialog.
- Success/partial-failure toasts for both bulk actions via the existing `useToast` primitive.
- New translation keys under `customers.*` in all three locale files.

### Changed
- Selection is cleared automatically when the filtered result set changes or after a bulk action completes.

### Verification
Full backend suite passing (537/537, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), and a live Playwright smoke test (bulk status change, bulk archive with confirm dialog, select-all) against a freshly seeded dev database — zero console errors.

## [2.20.0] — 2026-07-14 — Shareable/Persisted List Filters

Closes the next Version 1.1 item per the roadmap's own sequencing (pagination in 2.19.0, filter persistence here): Customers and Leads filter state (status/channel, search, sort) lived only in component state, so a filtered view could never be bookmarked or shared via URL. Frontend-only, no backend changes.

### Added
- New shared `useUrlFilters` hook (`frontend/lib/use-url-filters.ts`) — two-way syncs a list page's filter state with its URL query string via `router.replace` (no extra browser-history entries), reading the URL once on mount to hydrate initial state.
- Customers list page filters reflected in the URL: `?status=&search=&sort=&archived=1`.
- Leads list page filters reflected in the URL: `?channel=&search=&sort=`.

### Changed
- Both pages split into a thin default-export wrapper plus a `<Suspense>`-wrapped inner component, required by Next.js App Router whenever a statically-generated page calls `useSearchParams()`.

### Verification
Full backend suite passing (537/537, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes, `/crm/customers` and `/crm/leads` still statically prerendered), and a live Playwright smoke test confirming: setting filters updates the URL, navigating directly to a filtered URL restores the same filter state and results, and clearing filters returns the URL to its bare path — on both Customers and Leads, zero console errors.

## [2.19.0] — 2026-07-14 — "Load More" Pagination for Customers & Leads

Closes the last open Medium-priority Version 1.1 item: `GET /crm/customers`/`GET /crm/leads` have had a correct cursor-pagination contract all along, but neither list page ever consumed it — both silently capped at the default `limit=25`. Frontend-only, no backend changes.

### Added
- "Load more" button on the Customers and Leads list pages, wired to the existing `next_cursor`/`cursor` contract.
- Shared `common.loadMore` translation key across all three locale files (previously only existed under the `catalog` namespace).

### Fixed
- **Real bug found via live Playwright testing, not by reading code**: the "Load more" pattern being copied from the existing Catalog Materials page had a stale-closure bug — `reload`'s `useCallback` read a `cursor` state variable deliberately excluded from its dependency array, so `reload` was never recreated when `cursor` changed. Clicking "Load more" always re-fetched page one and appended it again, duplicating all rows forever and never reaching page two. This bug had already shipped, unnoticed, on the Materials page itself. Fixed at the root in all three pages (Customers, Leads, Materials): removed the redundant `cursor` state and changed `reload` to accept the cursor as an explicit call-time argument instead of reading it from a closure.

### Verification
Full backend suite passing (537/537, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), and a live Playwright smoke test against a freshly seeded dev database (30 customers, 30 leads, 30 materials) confirming the fix on all three pages — reproduced failing before the fix (duplicate rows, React key warnings) and passing after.

## [2.18.0] — 2026-07-13 — Full-App UX Audit

A from-scratch audit of every visible screen from a real G-STONE office employee's perspective — six parallel research passes covering every page and locale key. Frontend-only; no new module, no business-logic changes.

### Fixed
- **Global**: every date in the app rendered in English regardless of locale (`lib/format.ts` hardcoded `"en-US"`) — now reads the active locale via a new `activeDateLocale()` helper. Same fix applied to the Installation Calendar's month header and `charts.tsx`'s tooltip number formatting.
- Reports' `CategoryBarChart`/`TrendChart` showed raw English "No data for this period." on any empty date range across all five Reports pages — added the `emptyLabel` prop `StatusBarList` already had.
- Illegible dark-mode section headers (`bg-text-primary` + `text-white`, near-white-on-white) on CRM Task, Finance Invoice, Order, and Sales Quote builder detail pages — switched to `bg-primary`.
- Orders/Production/Installation/Finance Invoice detail pages each had a toggle button and confirm button sharing the exact same cancel-action label — the toggle now hides once the confirm card is open.
- Silent failures on write actions across the Sales Project workspace, Quote builder, Installation Kanban, and Installation Crews — none of these had `try/catch`, unlike every page Version 2.9.1 already covered. All now surface errors via toast/inline error.
- Raw UUIDs shown instead of names/numbers: Orders list, Order/Work-Order/Invoice detail pages, and the Material Prices table (which also had the wrong data under a mismatched "Currency" header) — resolved via client-side lookups against existing `GET`-by-id endpoints.
- ~30 untranslated English strings on the Communication Integrations page (credential field labels, provider dropdown, Queue/Diagnostics table values).
- Real mistranslations: Leads' `qualified` status, a Sales item type ("Moydadır" → "Lavabo dolabısı"), `projectType_stairs`/`itemType_stairs` inconsistency, Tasks' `recurrenceInterval`.
- Finance Expense/Invoice due-date fields used free-text inputs with an English placeholder instead of native date pickers; Expense category filter reused the generic "all statuses" key instead of a dedicated one.
- Material creation form's Material Type dropdown showed raw English options inside an Azerbaijani form.
- Customer detail page's two note boxes shared identical placeholder text; Customer profile's "Layihələr" tile was mislabeled "via Production"; Dashboard's "Gecikən layihələr" section linked to Orders, not Projects (renamed to match); login's company-role badges showed a raw backend role string; Tasks list wasn't sortable/searchable like its sibling pages; a Task's "Related to" link showed the generic word "Customer" instead of the actual name.

### Removed
- Dead/orphaned translation keys across all three locale files: `customerNew.type`/`customerProfile.type`/`customers.tableType`/the `customerType` namespace (closing a Version 1.1 backlog item verbatim), `dashboard.notifications`, `catalog.title`/`subtitle`/`tabSlabs`, `nav.quotes`, `orders.prodStatus_unassigned`/`instStatus_unassigned`, `tasks.relatedCustomer`.

### Deferred
Sales Photos tab shows captions only (no image thumbnails); Material detail has no inline spec editing; Slabs/Price-List material pickers aren't searchable; Reports KPI cards show no currency unit; Installation's tab bar isn't the shared `SectionTabs` component; per-channel badge colors — each recorded as out of proportion for this pass or in conflict with an existing convention, not silently skipped.

### Verification
Full backend suite passing (537/537, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), live smoke test against the real dev database and running backend.

## [2.17.0] — 2026-07-13 — Assigned Manager Picker

Closes the highest-priority remaining Version 1.1 item: the Customer form/profile had no real way to assign a manager, despite the backend fully validating the field since Phase 2.

### Added
- "Assigned Manager" dropdown (backed by `GET /api/v1/core/companies/users`) on the Customer creation form.
- The Customer profile page's manager field is now an editable dropdown instead of a raw UUID string.
- Toast confirmations on the Customer detail page for status change, manager change, note add, and the profile-notes save — the page previously had no `useToast` calls at all.
- 2 new backend tests covering explicit manager un-assignment and confirming an unrelated field update doesn't clear an existing assignment.

### Fixed
- `UpdateCustomerUseCase` (backend) could never actually clear `assigned_manager_id` — a PATCH body with `assigned_manager_id: null` was indistinguishable from the field being omitted entirely, since both read as Python `None`. A `clear_assigned_manager` flag, derived from `"assigned_manager_id" in payload.model_fields_set`, now makes "explicitly cleared" distinguishable from "not sent" for this one field, without changing PATCH-omission semantics for any other Customer field. Found via a live smoke test against the running dev API, not the automated suite.

### Verification
Full backend suite passing (537/537), frontend `tsc --noEmit` clean, frontend production build clean, live smoke test against the real dev database and running backend.

## [2.16.0] — 2026-07-10 — CSV Export for Customers & Leads

Closes the last Version 1.2 roadmap item never picked up: a standard CRM expectation (offline reporting, accounting handoff, marketing list pulls) that had been consistently deprioritized in favor of the Version 2.0+ module chain since 2026-07-01.

### Added
- `GET /api/v1/crm/customers/export` and `GET /api/v1/crm/leads/export` — CSV downloads honoring the exact same filters as their respective list endpoints (status/lead-source/search/sort for customers; status/channel/search/sort for leads), gated by the existing `crm:customers:read`/`crm:leads:read` permissions (no new permission introduced). Output is UTF-8 with a leading BOM so Excel renders Azerbaijani/Cyrillic characters correctly. Capped at 10,000 rows.
- "Export CSV" button on both the Customers and Leads list pages, next to the column-visibility menu, downloading the currently-filtered view via the existing `apiDownload` blob-download helper (the same mechanism Reports' PDF/Excel export and Sales' Quote PDF already use).
- 6 new backend tests (CSV shape, filter-respecting content, 401 without auth) across `test_customers_api.py`/`test_leads_api.py`.

### Verification
Full backend suite passing, frontend `tsc --noEmit` clean, frontend production build clean.

## [2.15.0] — 2026-07-10 — Sprint 6: Operational Dashboard Redesign

Replaces the generic CRM stats dashboard (customer/lead counters) with an operations-first view answering "what should our team do today?" — no new module, entirely inside the existing Dashboard page plus one small Sales endpoint to back it.

### Added
- `GET /api/v1/sales/measurements` — a company-scoped, date-range-filterable list of `ProjectItemMeasurement` rows (`ProjectItemMeasurementRepository.list_for_company`), backing the "measurements today" KPI. 1 new backend test (date-range filtering).
- Dashboard: time-of-day greeting ("Sabahınız xeyir" / afternoon / evening) using the logged-in user's real first name via `me()`, replacing the generic "Welcome back" + role line.
- Dashboard: four daily-ops KPI cards — measurements today, work orders in production, installations scheduled tomorrow, overdue work (overdue tasks + overdue orders combined).
- Dashboard: five new sections — Today's Tasks, Upcoming Installations, Overdue Projects (orders past their scheduled production/installation date), Notifications (merged task + installation notifications, newest first), and Recent Inquiries (replaces the old raw Leads table with the same data reframed as inbound inquiries).

### Changed
- Dashboard no longer shows raw customer/lead counters (active/archived customers, open/converted leads, leads-by-channel) — that pipeline-counter view is superseded by the daily-ops framing; the underlying Customer/Lead data and CRM screens are unaffected.
- `frontend/lib/api/sales.ts` gained `listMeasurementsForCompany()`; `az.json`/`ru.json`/`en.json`'s `dashboard` keys were rewritten to match the new sections (old `statActiveCustomers`/`myTasks`/`customersByStatus`-style keys removed, replaced with the new greeting/stat/section keys).

### Verification
Full backend suite passing, frontend `tsc --noEmit` clean, frontend production build clean.

## [2.14.0] — 2026-07-10 — UX & Production Polish Sprint

A frontend/wording-only audit pass ahead of daily use by G-STONE GALLERY's office staff — no new module, no business-logic or API changes.

### Changed
- The English word "Lead" (used untranslated inside otherwise fully Azerbaijani UI text — page titles, buttons, empty states, toasts, AI recommendation labels) replaced with "Potensial müştəri" consistently across the Dashboard, Leads, Reports, Quick Create, and AI Dashboard sections of `az.json`, matching the term the Leads/CRM tabs already used in a few spots.
- Generic "CRM" wording removed from the Dashboard subtitle and the Communication inbox's "not yet linked" message in all three locales (`az.json`/`ru.json`/`en.json`), replaced with plain "recent activity" / "customer record" phrasing.
- Fixed a real mistranslation: `subtotal` in `az.json` (Sales/Orders/Finance) was `"Arayış"` (Azerbaijani for "certificate/reference"), not a subtotal — corrected to `"Aralıq məbləğ"`.
- `catalog.isDefault` in `az.json` used the untranslated English word "Default" while the equivalent table header already said "Standart" — made consistent.
- The literal CRM-metaphor translation "Boru Kəməri" ("pipeline" as in oil pipeline) replaced with "proses"/"satış prosesi" wording across the AI Dashboard and Reports subtitle — the office-staff-facing term for "deals in progress," not a literal physical pipeline.
- Seed script's default owner account full name changed from the placeholder-sounding `"Platform Owner"` to `"G-STONE Admin"` (`backend/scripts/seed.py`) — this name is user-visible (e.g. "Welcome back, ...") the moment anyone signs in with the seeded account.
- Two English placeholder examples ("Team Alpha" crew name, "tesekkur" — missing diacritics on "təşəkkür") localized/fixed across `az.json`/`ru.json`/`en.json`.
- Sidebar navigation: every one of the 9 primary sections now has a small inline icon (matching the app's existing hand-drawn line-icon style, no new icon-library dependency) plus a left accent bar and softer highlight on the active item, replacing the flat text-only list.

### Verification
Full backend suite (528/528 passing, unchanged since only `seed.py`'s literal string changed), frontend `tsc --noEmit` clean, frontend production build clean (all 42 routes). A locale-file audit (every key in `az.json`/`ru.json`/`en.json` read end-to-end) found no remaining "Lead"/"CRM"/"Demo"/"Sample"/"Lorem ipsum"/"Dummy"/"Test" wording, and a repo-wide grep for the same terms plus `TODO`/`FIXME`/"Coming soon" across `frontend/app` and `frontend/components` came back clean.

## [2.13.0] — 2026-07-09 — The Complete Project Workflow

Turns the Project workspace into the full operational workflow G-STONE GALLERY runs a job through, end to end. Entirely inside the existing Sales module — no new module, no new nav entries.

### Added
- Project workspace expanded from 8 to 10 tabs, reordered to: Ümumi, Məkanlar, **Məmulatlar**, **Materiallar**, Ölçülər, Çertyojlar, Fotolar, İstehsal, Quraşdırma, **Təhvil**.
- "Məmulatlar" tab: a flat, project-wide table of every piece across every Room (room, type, stone, quantity, notes).
- "Materiallar" tab: pieces grouped by exact Stone + Thickness + Size combination, with item count and total quantity per group.
- `ProjectItem.completion_status` (new nullable column: `pending`/`delivered`/`accepted`) — "Təhvil" (handover to the customer) tracked per physical piece, distinct from `production_status`/`installation_status`.
- Two new Project Item types: `fireplace` (Kamin), `window_sill` (Pəncərə altlığı).
- Four new Room types: `corridor` (Dəhliz), `balcony` (Eyvan), `facade` (Fasad), `yard` (Həyət).
- 6 new backend tests.

### Changed
- "Təhvil" tab rebuilt from four static stat cards into a per-item editable status table (same pattern as the existing Production/Installation tabs), plus a small summary row.
- The curated "Məmulat" type picker now matches Sprint 5's authoritative 12-item list exactly (both `vanity` and `bathroom_furniture` offered together; `sink` no longer offered but stays valid for Items saved before this sprint).
- The curated "Məkan" type picker now matches Sprint 5's authoritative 8-item list (`staircase`/`exterior` no longer offered but stay valid for Rooms saved before this sprint — staircase work is now modeled as an `ITEM_TYPE_STAIRS` piece within any Room).

### Verification
Full backend suite (528/528 passing — 522 prior + 6 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes).

## [2.12.0] — 2026-07-09 — Production-Ready Material Selector

Normalizes the Brand → Stone → Thickness → Size flow: a Stone can now offer several thickness and size options instead of one free-text pair baked into the Material row, and every Project Item records exactly which option it was built with. Entirely inside the existing Catalog/Sales modules — no new module.

### Added
- `MaterialThickness`/`MaterialSize` (`catalog_material_thicknesses`/`catalog_material_sizes`): normalized option lists per Stone, full CRUD (add/list/delete), same sub-resource pattern as `MaterialImage`/`MaterialDocument`.
- `ProjectItem.material_thickness_id`/`material_size_id`: nullable FKs recording the specific option chosen for that item.
- Material detail page: "Thickness Options"/"Size Options" cards (list + add + delete), with `<datalist>` suggestions repurposed from Sprint 2's now-unused `SUGGESTED_THICKNESSES_MM`/`SUGGESTED_SIZES_MM`.
- Project workspace's "Add Item" form: Brand → **searchable** Stone (debounced server-side search) → Thickness → Size, the latter two populated from the selected Stone's own options.
- `SUPPORTED_BRANDS` curated suggestion list (NEOLITH, MARAZZI THE TOP, SAPIENSTONE, INALCO, ANATOLIA, BELENCO, COANTE) as `<datalist>` suggestions on the Brand creation form — `Brand.name` stays free text, no manufacturer specs stored.
- 8 new backend tests: Thickness/Size CRUD, per-material scoping, audit logging, and `ProjectItem` thickness/size selection.

### Changed
- Material creation form no longer collects thickness/dimensions at Stone-creation time — those are now added afterward via the detail page's new option cards. The legacy `thickness_mm`/`dimensions` columns on `StoneMaterial` are untouched (backward compatible with existing Materials).
- Migration adds `sales_project_items`' two new FK columns via a SQLite-safe `batch_alter_table` (SQLite can't `ALTER TABLE ADD CONSTRAINT` directly; verified with a full upgrade/downgrade/upgrade round-trip).

### Verification
Full backend suite (522/522 passing — 514 prior + 8 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes).

## [2.11.0] — 2026-07-09 — Measurement & Room Management

Makes "Layihə" (Project) genuinely the primary business object: a Project now contains Rooms, each Room contains Project Items (the physical pieces being fabricated), and each Project Item owns its Material, Measurement history, Drawings, and Photos. Built entirely inside the existing Sales module (no new module) — an initial plan to build Measurement/Room as standalone modules was corrected mid-sprint to avoid duplicating the Project/Quote structure that already exists there.

### Added
- **`Room`** (`sales_rooms`): kitchen/bathroom/living_room/staircase/exterior/custom, scoped to a Project, with an optional custom label.
- **`ProjectItem`** (`sales_project_items`): the curated piece vocabulary from Sprint 2 (countertop, island, sink *(new)*, tv_panel, vanity, wall_cladding, flooring, stairs, table, other), scoped to a Room, with a Brand→Stone→Thickness→Size Material reference (never free text), quantity, production status, and installation status.
- **`ProjectItemMeasurement`** (`sales_project_item_measurements`): every recorded measurement is a new revision (never an overwrite) — length/width/thickness, computed area, measurer name, measurement date, notes, and an attachable customer signature.
- **`ProjectItemDrawing`** / **`ProjectItemPhoto`**: DWG/DXF/sketch/PDF drawings and site photos attached to a Project Item, backed by the existing core `documents` store (same pattern as Catalog's material documents/images).
- New Sales API endpoints for all of the above (`/sales/projects/{id}/rooms`, `/sales/rooms/{id}/items`, `/sales/project-items/{id}/measurements`, `.../drawings`, `.../photos`) — all gated by the existing `sales:projects:read`/`write` permissions, no new permission strings.
- Project detail page rebuilt into a tabbed workspace: Overview, Rooms, Measurements, Drawings, Photos, Production, Installation, Completion.
- 22 new backend tests (`tests/sales/test_rooms_and_project_items.py`): CRUD, revisioning, cross-tenant isolation, audit log + domain event coverage for every write action.

### Changed
- `core/storage/router.py`'s upload allowlist extended to accept DWG/DXF files (by MIME type or, for the common `application/octet-stream` browser fallback, by filename extension) — required for the Drawings tab.

### Verification
Full backend suite (514/514 passing — 492 prior + 22 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes).

## [2.10.0] — 2026-07-09 — G-STONE Sprint 2: Simplified Navigation & Layihə-Centric Workflow

A usability restructuring driven by real G-STONE office feedback that the app read like accounting software rather than a gallery workflow tool. Re-anchors the UI around "Layihə" (Project) and its pieces, and pushes 1C's territory (warehouse/stock/accounting) out of daily view. No backend schema changes; nothing was deleted, only regrouped.

### Changed
- **Primary sidebar reduced from ~20 flat entries to 9 module-level sections**: İdarə Paneli, Müştərilər, Layihələr, Materiallar, İstehsal, Quraşdırma, Mesajlar, Hesabatlar, Ayarlar — the "module-level primary nav, secondary nav within a module" structure `UI_UX_GUIDELINES.md` §6.1 always called for. Everything that used to have its own sidebar entry is still reachable, either via a new `SectionTabs` in-page tab bar (`components/ui/section-tabs.tsx`) on the CRM, Catalog, and Sales/Orders pages, or from the new `/settings` hub below.
- **New `/settings` hub page** groups back-office pages that don't belong in daily use: Channels/Templates/Integrations (messaging admin), Warehouses/Slabs/Price Lists (Catalog admin), and Orders/Invoices/Expenses/AI Assistant (oversight convenience links). Uses the `settings.*Desc` translation keys added in a prior session but never wired to a page until now.
- **`nav.catalog` renamed** from "Daş Kataloqu" / "Каталог камня" / "Stone Catalog" to "Materiallar" / "Материалы" / "Materials" in all three locale files — plainer office terminology.
- **Material creation form** (`catalog/materials/new`): `thickness`/`dimensions` changed from free-text inputs to curated dropdowns (common slab thicknesses/sizes) with a manual "Other" fallback, presenting entry as a Brand → Stone → Thickness → Size cascade ahead of a future supplier-catalog import. No manufacturer spec data was hardcoded — only everyday defaults.

### Added
- **Seven new Sales `item_type` values** — `countertop`, `island`, `tv_panel`, `bathroom_furniture`, `flooring`, `stairs`, `table` (Mətbəx dəzgahı, Ada, TV paneli, Hamam mebeli, Döşəmə, Pilləkən, Masa) — added to `VALID_ITEM_TYPES` / `MATERIAL_ITEM_TYPES` / `ITEM_TYPE_DEFAULT_UNIT` in `modules/sales/domain/value_objects.py`. Each new type is a physical piece, not a billing-only line, and rides on the existing per-item `material_id`/`production_status`/`installation_status` fields `OrderItem`/`QuoteSectionItem` already had — only the controlled vocabulary grew, no migration needed.
- Translated labels for every item type (`sales.itemType_*`, all 19 values, in all three locale files) — fixes a pre-existing i18n gap where the Quote builder and Order detail pages rendered the raw English slug (e.g. `wall_cladding`) verbatim instead of a translated label.

### Fixed
- `crm.title`/`crm.subtitle` keys were present in `ru.json` but missing from `az.json`/`en.json` (a partial addition left over from a prior session); added for parity.

### Verification
Full backend suite (492/492 passing), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes, including the new `/settings` route).

## [2.9.3] — 2026-07-08 — Production Readiness follow-up: i18n, dark mode, breadcrumbs

A second pass over the four Phase 3 research findings that landed after 2.9.2 was already committed: an i18n audit, a responsive/dark-mode audit, a navigation/breadcrumb audit, and a CRUD-completeness audit. No new features, no business-logic changes.

### Fixed
- **`az.json` had one untranslated string**: `catalog.tableDefault` was left as the literal English `"Default"` even though Azerbaijani is the app's default locale, so every AZ user saw raw English on the Price Lists table's "Default" column. Translated to `"Standart"`, consistent with the existing `"standart"` usage elsewhere in the same file.
- **Dashboard/Reports chart gridlines and data-point strokes were hardcoded to light-mode hex colors** (`components/ui/charts.tsx`): gridlines used a fixed `#E2E5EA` (the light theme's border color) and point strokes used a fixed `#FFFFFF`, so both were nearly invisible or wrong against a dark background. Switched both to the existing `--color-border`/`--color-surface` CSS custom properties, which already repoint automatically between light and dark (same mechanism every other themed element in the app uses) — verified live in a browser with the dark-mode toggle active.
- **Breadcrumb inconsistency across detail pages**, flagged as a known gap as far back as the 2.9.1 changelog entry: only the Customers detail page had real breadcrumbs; the other nine (Orders, Production, Catalog Materials, Catalog Price Lists, CRM Tasks, Finance Invoices, Installation Jobs, Sales Projects, and the Sales Quote builder) used a plain "← Back to X" link instead. Extracted a shared `Breadcrumb` component (`components/ui/breadcrumb.tsx`) from the Customers page's existing markup and applied it to all ten pages; the Quote builder now shows the full three-level trail (Projects / project name / quote number). Verified live for five of the ten pages with real records (the rest share the identical, type-checked pattern against empty tables in the current dev database).

### Removed
- Eight now-orphaned `backTo*`/`back` translation keys (`orders.backToOrders`, `production.backToWorkOrders`, `finance.backToInvoices`, `tasks.backToTasks`, `installation.backToInstallation`, `sales.backToProjects`, `sales.backToProject`, `catalog.materialDetail.back`) from all three locale files, left dead by the breadcrumb replacement above. `tasks.backToPending` (a different, still-used string) was left untouched.
- Two small pre-existing dev artifacts found while editing these same files: an unused `updateProject` import on the Sales Project detail page, and an unused `CardHeader` import left over from 2.9.2's Quote Settings panel.

### Corrected
- **Investigated and declined a finding from an earlier research pass**: CRM Customer archive was reported as missing a "Restore" button in the UI, with the assumption that the existing `PATCH /crm/customers/{id}` endpoint could already un-archive a customer. On inspection, `UpdateCustomerUseCase` never touches `deleted_at` — only `ArchiveCustomerUseCase` does, and no restore use case exists anywhere in the backend. Adding one would be new business logic, out of scope for this pass; recorded as a genuine, not-yet-built gap instead of a wiring fix.
- **Considered and declined adding a sidebar icon library.** `UI_UX_GUIDELINES.md` calls for one consistent icon set across all ~20 nav items; the sidebar has been text-only since day one. This is a real design-system decision (icon set choice, sizing, every nav entry and page header touched) rather than a bug fix, so it was left as a documented, deliberately deferred gap rather than partially addressed.

### Verification
Full backend suite (492/492 passing, unchanged from 2.9.2 since no backend files were touched), frontend `tsc --noEmit` clean, frontend production build clean (all 41 routes), and a live end-to-end Playwright smoke test against the real dev database and both running servers: login, company selection, every touched list page, and five of the ten breadcrumb-refactored detail pages (Customers, Sales Projects, CRM Tasks, Catalog Price Lists, and the Sales Quote builder) exercised with real records and zero console errors; dark mode toggled live and the chart color fix confirmed via computed style (gridline stroke resolves to the dark theme's border color, not the old hardcoded light hex).

## [2.9.2] — 2026-07-08 — Production Readiness & G-STONE Onboarding

Phase 3: a full application-perspective audit ahead of real daily use by G-STONE GALLERY — every navigation item, CRUD flow, filter/sort/export, permission path, company switch, responsive/dark-mode/i18n behavior, and loading/empty/error state reviewed. Four independent research passes (backend security/demo-data, frontend branding/demo-data, navigation/i18n/UX-states, CRUD/filters/permissions/company-switching) plus a live end-to-end Playwright smoke test against the real dev database. No new features, no business-logic changes. See `PRODUCTION_READINESS_REPORT.md` for the full audit findings, including items considered and deliberately deferred.

### Fixed
- **Sales → Projects "create project" form was completely broken**: `listCustomers({ limit: 200 })` requested more rows than the `GET /crm/customers` endpoint allows (`le=100`), so every load of the customer dropdown 400'd and the picker silently rendered empty — Create was unusable from that form. Capped the request at 100.
- **Orders list `sort` parameter was accepted but silently ignored**: the API and frontend wrapper both had a `sort` field, but `OrderRepository.list()` always ordered by `created_at desc` regardless of its value. Wired it to a real `_SORTABLE` field map (`order_number`, `status`, `created_at`, `total_final`), matching the pattern already used by `ProjectRepository`.
- **Sales Quotes had no way to edit VAT rate, discount, currency, validity date, or notes after creation** — the backend `PATCH /quotes/{id}` endpoint and its translation keys existed but nothing in the UI called it, so every quote was stuck with its creation-time defaults. Added an editable "Quote Settings" panel to the quote builder page, active while a quote is in `draft`.
- **Frontend `Quote.discount_type` TypeScript type didn't match the backend**: declared `"percentage"` where the backend only recognizes `"percent"` (`totals.py`). Dormant only because no UI ever set the field; would have silently produced a zero discount the moment the new settings panel started sending it. Fixed the type and used the correct value.
- **Catalog Brands and Warehouses had no archive/restore affordance**: `PATCH .../status` existed and worked (Materials already used it), but the Brands/Warehouses list pages never exposed it. Added an Active/Hidden toggle button per row, and both lists now include hidden entities so a restore path exists.
- Missing favicon — added `frontend/app/icon.svg` (Next.js's file-based icon convention), a simple "G" monogram in the app's primary color. Browser tabs previously showed a generic/blank icon.
- Browser tab title was the same static "G-STONE ERP" on every one of the ~30 routes. `AppShell` now sets `document.title` to the active section's translated nav label on every in-app (client-side) navigation. Known remaining limitation: because the entire `(app)` route group is client-rendered behind a token-check gate (no per-route `generateMetadata` is possible without restructuring every page to a server-component wrapper), a hard page reload or a directly-opened/bookmarked URL still shows the static app-wide title until the next in-app navigation — documented as a follow-up rather than fixed here.

### Changed
- Sales Projects list gained the status filter and sortable-column headers every sibling list page already had (backend already supported both `status` and `sort` query params; the frontend simply never wired them up).
- Removed two dead, unused translation keys (`sales.serviceSettings` / `sales.servicePriceUpdated`, orphaned from an earlier abandoned feature) from all three locale files and repurposed the slots for the new Quote Settings UI strings (`quoteSettings`, `discountTypeNone/Percent/Fixed`, `discountValue`) — key parity across `en.json`/`az.json`/`ru.json` maintained.

### Verification
Full backend suite (492/492 passing), frontend `tsc --noEmit` clean, frontend production build clean (all 41 routes), and a live end-to-end Playwright smoke test against the real dev database and both running servers: login, company selection, every touched page loaded with zero console/HTTP errors, a real brand created and its archive/restore toggle exercised, and a real project → quote created with its new Quote Settings panel edited and confirmed persisted across a page reload.

## [2.9.1] — 2026-07-07 — Enterprise Polish

Production-readiness audit across all ten shipped modules (CRM, Tasks, Communication, AI, Sales, Orders, Production, Installation, Finance, Reports). No new features, no business-logic changes, no API contract changes.

### Fixed
- Orders, Production, Finance Invoice, and Installation Job detail pages: write-action handlers (`handleCancel`, `handleAdvance`, `handleSend`, `handleMarkOverdue`, `handleComplete`, `handleSaveDetails`, and related) had no error handling at all — a failed request produced no feedback whatsoever. Now surfaced via the existing `useToast` primitive.
- `crm/tasks/new`: the success toast was imported and instantiated but never actually invoked; the submit button still used the old manual disabled/text-swap pattern instead of `Button`'s `loading` prop.
- The `customerCreated`/`taskCreated` translation keys referenced by `crm/customers/new` and `crm/tasks/new` were missing from all three locale files (`az.json`, `ru.json`, `en.json`).
- `Toast`'s dismiss button had a hardcoded English `aria-label="Dismiss"` instead of a translation key.
- `test_app_boots_in_production_with_a_real_secret` didn't account for the new channel-credentials-key boot guard (added mid-session); added a dedicated regression test for that guard and updated the existing test to patch both secrets.

### Changed
- Communication module: added application-level logging (`logger.warning`/`logger.exception`) alongside the existing `IntegrationLogEntry` DB record in every webhook, send, queue-retry, and IMAP-sync error path. Previously these failures were visible only in the app's own database tables.
- Sales quote acceptance (`_check_slab_availability`/`_reserve_slabs`/`_release_slabs`): batched into a single `Slab.id.in_(...)` query instead of one `db.get()` per line item, and consolidated behind one `_quoted_slabs_by_id` helper. Behavior, including error messages, is unchanged.
- Consolidated duplicated table-wrapper styling (`overflow-x-auto rounded-lg border border-border bg-surface` + sticky `thead` classes) across 8 list pages (Catalog Brands/Materials/Price Lists/Slabs/Warehouses, Orders, Production, Sales Projects) into the shared `tableScrollShellClass`/`stickyTheadClass` constants already used elsewhere.
- Hardened `core/bootstrap/app_factory.py`'s production-boot guard to also refuse to start with the default `CHANNEL_CREDENTIALS_ENCRYPTION_KEY` outside development, alongside the existing JWT-secret check.
- `core/api/errors.py`'s unhandled-exception handler now logs the exception with the same `request_id` returned to the caller.
- `ConfigureChannelCredentialUseCase` now validates a provider's required config fields at configuration time (clean `400`) instead of only failing the first time something tries to use an incomplete credential.
- `SendMessageUseCase`/`TestChannelConnectionUseCase` now catch provider-construction failures gracefully instead of raising an unhandled `500`.

### Verification
Full backend suite (489/489 passing), frontend `tsc --noEmit` clean, frontend production build clean (all 41 routes), and a live end-to-end smoke test (login, company switch, every touched page, a real customer created through the UI) confirmed no regressions.

## [2.9.0] — 2026-07-06 — Real Integrations

Real WhatsApp Business Cloud API, Instagram Messaging API, Messenger Send API, SMTP+IMAP email, and Twilio SMS providers for the Communication Center, plus a generic webhook provider for arbitrary partner systems. Encrypted per-channel credentials (Fernet), connection testing, health monitoring, signature-verified inbound webhooks, delivery/read status sync, a retry queue for failed sends, and a Provider Diagnostics/Webhook Monitor admin page. `ChannelProvider` interface unchanged; a channel with no credential configured still uses `NullChannelProvider` exactly as before. 61 new backend tests (488/488 total).

## [2.8.1] — 2026-07-06 — UX & Platform Polish

Frontend-only cross-cutting pass: design-system token layer (Montserrat font, CSS-variable-based colors) with dark mode, an improved table toolkit (column resize/visibility, sticky headers, saved filters) on the busiest list pages, better form loading/validation/success feedback, a mobile slide-over navigation drawer, accessibility baseline (focus-visible, skip link), and print-friendly layouts. Zero backend files changed; no API contracts changed.

## [2.8.0] — 2026-07-06 — AI Sales Assistant

Provider-agnostic AI recommendations (lead scoring, conversation intelligence, quote intelligence, task suggestions) across CRM, Communication, Sales, and Tasks, with a dedicated AI Dashboard. Every recommendation requires an explicit human Accept/Reject/Edit; no real LLM provider wired up yet, by design. 79 new backend tests (427/427 total).

## [2.7.0] — 2026-07-06 — Communication Center

Unified omnichannel inbox (WhatsApp Business, Instagram Direct, Facebook Messenger, Email, SMS) integrated with CRM, with a provider abstraction layer standing in for real channel integrations. 36 new backend tests (348/348 total).

## [1.2.0] — 2026-07-06 — Tasks & Reminders

Full CRUD, assignee/priority/tags/due-date/status, recurring tasks, and in-app notifications, built inside the CRM module. 42 new backend tests (312/312 total).

## [2.6.0] — 2026-07-06 — Finance

Invoicing (draft → sent → partially_paid/overdue → paid) and payments, plus a standalone Expense entity. 31 new backend tests (270/270 total).

## [2.5.0] — 2026-07-04 — Installation

Installation job scheduling and lifecycle, crew management, photo/signature capture, in-app notifications. 38 new backend tests (239/239 total).

## [2.4.0] — 2026-07-04 — Production

Work orders (queued → cutting → polishing → quality_check → completed/cancelled) consuming slab-linked order items. 8 new backend tests (219/219 total).

## [2.3.0] — 2026-07-04 — Reports

Executive Dashboard, Sales/Production/Installation/Finance Analytics, cross-module KPI cards, charts, date-range filtering, PDF/Excel export.

## [2.1.0–2.2.0] — 2026-07-01 — Sales & Orders

Projects, Quotes (sections, measurements, items, PDF export), and Orders (status workflow from an accepted Quote through production/installation/completion).

## [2.0.0] — Stone Catalog

Brand, Collection, Stone Material, Slab (lifecycle + per-company unique slab numbers), Warehouse, Price List, and Material Image/Document linking.

## [1.0.0] — CRM

Auth, RBAC, audit log, event bus; stone-industry Customer model, Lead capture across 9 channels, Dashboard, search/sort/keyboard shortcuts.
