# G-STONE ERP — Implementation Report

_Date: 2026-07-22 (original report), addended 2026-07-22 (Version 2.36.0 / Phase 17)_
_Scope: everything implemented since the last audit (`PROJECT_AUDIT.md`, dated 2026-07-21, frozen at commit `521428e` / Version 2.25.0), through current HEAD commit `797aa57` (Version 2.33.0). Sections 1–8 below are the original report, kept as written — they describe what was true at the time. §9 is a same-day addendum covering Phase 17 (Version 2.36.0), added because it directly resolves several items §8 originally listed as "Still open"; those table rows are annotated below rather than silently rewritten, consistent with this project's practice of recording corrections rather than erasing history. (Versions 2.34.0 and 2.35.0, the two Stone Fabrication Workflow phases, are covered by their own dedicated `STONE_WORKFLOW_REPORT.md`, not repeated here.)_
_Method: `git log`/`git diff --stat` against the audit baseline commit, cross-checked against `CHANGELOG.md` entries for each release, plus direct re-verification of every "remaining issue" claim against the current source (not assumed from the prior audit text)._

This window covers **9 commits, 179 files changed, +11,409 / −945 lines**, and the backend test suite grew from 553 to 630 passing. Every numbered item in the prior audit's Priority List (§11, items 1–5) was addressed in this window, in order, plus three entirely new modules were shipped beyond what the audit's remaining-work estimate scoped for a single window.

---

## 1. Features Added

### 1.1 Pagination Rollout — v2.26.0 (closes Priority #1 / B4 / P1)
- Added "Load more" UI to **Orders, Production (work orders), Finance Invoices, Finance Expenses** — all four already had full cursor support in the backend and `lib/api/*.ts`; only the page components had never consumed `next_cursor`.
- **Catalog Brands** was a genuine backend gap: `GET /api/v1/catalog/brands` never accepted `limit`/`cursor` and silently truncated at 50 rows. Added `limit`/`cursor` params and `next_cursor` to `BrandListOut`, matching the Materials/Slabs pattern.
- Investigated Catalog Warehouses and Price Lists and found **no bug** — neither applies a `LIMIT` at all, so both already return every row; no UI was added (would be pagination theater).

### 1.2 Dashboard Resilience & Accurate KPIs — v2.27.0 (closes Priority #2 / B2 / B3 / P2)
- Replaced the Dashboard's `Promise.all` fan-out with `Promise.allSettled` — a single failing call (e.g. a transient error on Inventory Analytics) previously blanked the *entire* page; now each of the 9 calls resolves independently.
- Decoupled JSX gating so the KPI/revenue-trend section (needs `executive` data) no longer hides unrelated "Today" sections (tasks, installations, overdue orders, notifications, recent inquiries) when only the executive call fails.
- Fixed silent KPI under-counting: `Orders`, `Production`, and `Installation Jobs` were fetched with a hardcoded `limit: 100` and no follow-up. Added `lib/fetch-all-pages.ts` (generic cursor-follower, capped at 50 pages as a runaway-loop safety valve) and applied it to all three.
- "Recent Inquiries" now requests exactly `{ sort: "-created_at", limit: 5 }` instead of fetching 100 leads and slicing client-side.
- Customer/project name lookups for Overdue Projects and Upcoming Installations replaced bulk 100-row fetches with targeted per-id lookups (`getCustomer`/`getProject`).

### 1.3 Real CI Enforcement of the Core/Module Boundary — v2.28.0 (closes Priority #3 / S2)
- Added `.github/workflows/ci.yml`: two jobs — **backend** (`pip install`, `pytest`, `lint-imports`) and **frontend** (`npm ci`, `npm run typecheck`, `npm run build`) — on every push/PR to `main`.
- Added `import-linter==2.13` to `backend/requirements.txt` (previously configured in `pyproject.toml` but never actually installable).
- Fixed `pyproject.toml`'s `[tool.importlinter]` config — `root_package = "core"` with `forbidden_modules = ["modules"]` made `lint-imports` error immediately instead of evaluating anything, because `modules` sits outside the one declared root package. Changed to `root_packages = ["core", "modules"]`. Verified with a deliberately-introduced `core → modules` import that `lint-imports` correctly flagged it, then reverted and re-verified clean.
- Updated `backend/README.md` and `CLAUDE.md` to document `lint-imports` as a real, runnable command.

### 1.4 Documentation Sync — v2.29.0 (closes Priority #4)
- Full rewrite of `API_SPECIFICATION.md`: replaced the fictional Phase-1 CRM (Contacts/Accounts/Deals/Pipeline-Stages) and flat Sales (Quotes/SalesOrder) design-sketch content with the real, shipped endpoint surface. Added first-time coverage for Production, Installation, Finance, Reports. Corrected multiple drifted claims (logout body/behavior, Brands cursor pagination, events-log endpoint's real owner-only check, file-upload's actual fixed permission and 10 MB/content-type limits, the undocumented `GET /core/companies/users` endpoint, and the fact no endpoint uses the originally-planned `202 Accepted` async pattern).
- Full rewrite of `DATABASE_DESIGN.md`: replaced the fictional schema with real `crm_customers`/`crm_contacts`/`crm_leads`/`crm_tasks` and `sales_quotes`/`sales_projects`/`orders` tables; added first-time coverage of Production/Installation/Finance schemas; confirmed Postgres RLS is **not implemented anywhere**; confirmed refresh-token revocation lives in Redis/in-memory, not a DB column; confirmed CI-vs-test-suite migration bypass (tests use `Base.metadata.create_all()`, not the real migration chain); documented the known `crm_customers`↔`crm_contacts` circular FK (B5).
- `README.md` and `ROADMAP.md` brought current through v2.28.0.

### 1.5 Cursor Bug Fix — v2.30.0
- `GET /orders`, `/production`, `/installation/jobs`, `/finance/invoices`, `/finance/expenses` accepted `limit`/`cursor` and used them in the query, but **hardcoded `next_cursor=None`** in every response regardless of whether more rows existed — this silently defeated the v2.26.0 "Load more" UI. Fixed all five to fetch `limit + 1` rows and return a real `encode_cursor(...)` cursor when a next page exists.

### 1.6 Purchasing Module (new) — v2.31.0 (closes Priority #5)
- **Suppliers** — full CRUD, active/hidden status, cursor-paginated list with search.
- **Purchase Orders** — created against an active supplier with ≥1 line item (optionally linked to a `catalog_materials` row, or free-text non-material cost like freight). Status lifecycle `draft→sent→confirmed→{partially_received,received}/cancelled`; only `sent`/`confirmed`/`cancelled` are manually settable, `(partially_)received` only as a side effect of receiving. Only `draft` orders can still have notes/expected-delivery-date edited.
- **Receiving** — `POST /purchase-orders/{id}/lines/{line_id}/receive` accumulates `quantity_received` (capped at ordered quantity) and, given a warehouse + slab number, creates a **real `catalog_slabs` row** by reusing Catalog's own `CreateSlabUseCase` — the inverse of Production's existing `UpdateSlabStatusUseCase` consumption pattern.
- **Frontend**: `/purchasing/suppliers`, `/purchasing/orders` (list + status filter), `/purchasing/orders/new` (supplier picker, repeatable line-item rows, live estimated total), `/purchasing/orders/[id]` (status actions, inline receiving form, receipt history). Reachable from `/settings`.

### 1.7 Marketing Module (new) — v2.32.0 (closes Priority #5 — original 10-module plan now complete)
- **Campaigns** — `name`, `channel`, `budget`/`currency`, `start_date`/`end_date`, `notes`, lifecycle `draft→active→{completed,cancelled}`.
- **Lead attribution** — `crm_leads.campaign_id` (nullable, indexed, no DB-level FK — same polymorphic-reference pattern as `documents.related_entity_id`); CRM itself gains no dependency on Marketing.
- **Performance** — `GET /marketing/campaigns/{id}/performance`, computed live (not cached/stored): `leads_count`, `converted_count`, `conversion_rate`, `attributed_revenue` (sum of `total_final` across converted customers' orders, counting only `ready`/`delivered`/`installed`/`completed` statuses so cancelled orders never inflate ROI). Verified company-scoped via a deliberate cross-tenant `campaign_id` collision test.
- **Frontend**: campaign picker added to the Lead capture form; `/marketing/campaigns` (list + inline create) and `/marketing/campaigns/[id]` (live performance stat cards, status actions). New "Marketing" group on `/settings`.

### 1.8 Customer Portal (new, beyond original 10-module scope) — v2.33.0
- **Separate customer auth identity** — `customer_portal_logins` (1:1 real FK to `crm_customers`). JWTs carry `"type": "customer_access"`/`"customer_refresh"` (vs. staff's `"access"`/`"refresh"`) with only `customer_id`/`company_id`, no role/permissions. `get_current_customer` and staff's `get_current_user` each reject the other's token type (tested both directions + live smoke-tested).
- **Staff-side access management** (`/customer_portal/admin/...`) — enable access, reset password, enable/disable, each producing an audit entry + domain event.
- **Customer-facing auth** (`/customer_portal/auth/...`) — login (separate 10/minute/IP rate-limit bucket from staff), refresh, logout-everywhere.
- **Customer-facing read surface** (`/customer_portal/me/...`) — profile, orders, quotes, invoices, installation jobs, documents; every query hard-scoped to `(company_id, customer_id)` from the token, never a client-supplied filter. Dedicated whitelisted schemas (`PortalOrderOut` etc.) never expose `total_internal_cost`/`total_profit`/`profit_margin_pct`/`internal_notes`. Draft quotes/invoices return `404` on direct fetch. Documents limited to the customer's own CRM attachments + their own installation-job photos.
- **Frontend**: "Customer Portal" card on the Customer detail page for staff; a separate `/portal/...` route tree with its own login page, session storage, and API client (distinct from the staff app): dashboard, orders (list/detail), quotes (list/detail), invoices (list/detail), installation (list), documents.
- Verified with a live end-to-end smoke test against the running app and dev database, not just the automated suite.

---

## 2. Files Changed

| Commit | Files | Insertions | Deletions |
|---|---|---|---|
| `fc9bcdd` Pagination rollout | 11 | +485 | −142 |
| `0830730` Dashboard hardening | 3 | +210 | −109 |
| `988253b` CI + import-linter | 6 | +97 | −4 |
| `0b40255` Doc sync | 5 | +830 | −697 |
| `3feb128` Cursor bug fix | 12 | +372 | −22 |
| `bb2ed5a` Purchasing module | 59 | +3,874 | −23 |
| `3168764` Marketing module | 57 | +2,007 | −23 |
| `797aa57` Customer Portal | 63 | +3,627 | −18 |
| **Total** | **179** | **+11,409** | **−945** |

New top-level backend module directories: `backend/modules/purchasing/`, `backend/modules/marketing/`, `backend/modules/customer_portal/` (each with full `domain/application/infrastructure/presentation` Clean Architecture layering).

New top-level frontend route trees: `frontend/app/(app)/purchasing/`, `frontend/app/(app)/marketing/`, `frontend/app/portal/` (separate, unauthenticated-from-staff's-perspective tree with its own `layout.tsx`, `login/`, `dashboard/`, `orders/`, `quotes/`, `invoices/`, `installation/`, `documents/`).

New `lib/api/` files: `purchasing.ts`, `marketing.ts`, `portal.ts`, `customer-portal-admin.ts`.
New supporting frontend libs: `lib/fetch-all-pages.ts`, `lib/portal-session.ts`, `lib/portal-api-client.ts`.

---

## 3. Database Changes

Three new Alembic migrations, all generated via `alembic revision --autogenerate` and confirmed `alembic check`-clean against the actual dev database:

| Migration | Tables added | Notes |
|---|---|---|
| `4c0488d40756_purchasing_module_tables.py` | `suppliers`, `purchase_orders`, `purchase_order_lines`, `goods_receipts` | 146 lines |
| `430944e10164_marketing_module_tables_and_crm_leads_.py` | `campaigns` + `crm_leads.campaign_id` | 57 lines; new column has no FK constraint by design |
| `2b84b718b162_customer_portal_module_tables.py` | `customer_portal_logins` | 49 lines; genuine 1:1 FK to `crm_customers.id` |

No schema changes were required for the pagination/dashboard/CI/doc-sync work (v2.26.0–v2.30.0) — those were application-logic and tooling fixes only.

`DATABASE_DESIGN.md` was also brought current (documentation only, no schema change) to reflect Production/Installation/Finance's real, previously-undocumented tables, and to explicitly flag that RLS is not implemented and that the circular `crm_customers`↔`crm_contacts` FK (B5) still exists.

---

## 4. API Changes

- **+12 Purchasing endpoints**: Suppliers CRUD + list; Purchase Orders create/list/get/patch/status; line receiving; receipt history.
- **+6 Marketing endpoints**: Campaigns CRUD + list, status transition, performance.
- **+18 Customer Portal endpoints**: staff admin (enable/reset/status) + customer auth (login/refresh/logout) + customer read surface (profile/orders/quotes/invoices/installation/documents).
- **5 existing endpoints fixed** (not added): `GET /orders`, `/production`, `/installation/jobs`, `/finance/invoices`, `/finance/expenses` now return a real `next_cursor` instead of always `null`.
- **1 existing endpoint extended**: `GET /catalog/brands` gained `limit`/`cursor` params and `next_cursor` response field.
- `API_SPECIFICATION.md` §20 (Purchasing), §21 (Marketing), §22 (Customer Portal) document the full contracts; the pre-existing full-document rewrite in v2.29.0 also corrected several previously-inaccurate claims (see §1.4 above).

---

## 5. Frontend Changes

- Route count grew **39 → 55** (16 new routes) across the three new modules.
- i18n key count grew to **1,414 keys**, verified at exact parity across `az.json`/`ru.json`/`en.json` at every release in this window.
- Dashboard page (`app/(app)/dashboard/page.tsx`) rewritten for resilient fetching (§1.2).
- Customer detail page gained a "Customer Portal" access-management card.
- Lead capture form gained a live active-campaign picker.
- `/settings` hub gained two new module groups: "Purchasing"/"Təchizat"/"Снабжение" and "Marketing"/"Marketinq"/"Маркетинг".
- Every release in this window re-verified `tsc --noEmit` clean and a clean `next build` before being marked done.

---

## 6. Tests Added

**77 new backend tests: 553 → 630 passing.**

| Area | New tests | Notable coverage |
|---|---|---|
| Pagination cursor fixes (v2.26.0/v2.30.0) | 6 | 1 Brands cursor test; 5 "cursor reaches the next page" tests for Orders/Production/Installation/Finance invoices/expenses |
| Purchasing (`tests/purchasing/`) | 24 | Supplier CRUD/search/pagination; PO creation (totals, empty-lines/inactive-supplier rejection); full status transition graph incl. illegal transitions; receiving (full/partial/over-receipt/wrong-endpoint rejections); multi-company isolation; PO-number sequencing; audit+event coverage |
| Marketing (`tests/marketing/`) | 16 | Campaign CRUD/search/pagination; full status transition graph; update-blocked-when-terminal; performance with no leads / mixed conversion / cancelled-orders-excluded; cross-tenant `campaign_id` collision isolation test; audit+event coverage |
| Customer Portal (`tests/customer_portal/`) | 31 | Access-management CRUD/permission/conflict/not-found; login/refresh/logout incl. two deliberate cross-token-type rejection tests; full read surface incl. ownership enforcement (another customer's order → 404), draft-hiding for quotes/invoices, document visibility exclusions |

Also fixed in-flight: `tests/purchasing/` and `tests/marketing/` were both missing `__init__.py`, causing a pytest module-name collision between their identically-named `test_isolation_and_events.py` files the moment both packages existed — added both files, matching the established per-module pattern.

Every release confirmed `lint-imports` passing (1 contract kept, 0 broken) once that gate existed (from v2.28.0 onward).

---

## 7. Git Commits (chronological)

| Commit | Version | Summary |
|---|---|---|
| `fc9bcdd` | 2.26.0 | Pagination Rollout (Priority #1) |
| `0830730` | 2.27.0 | Dashboard Resilience & Accurate KPI Counts (Priority #2) |
| `988253b` | 2.28.0 | Real CI Enforcement of the Core/Module Architecture Boundary (Priority #3) |
| `0b40255` | 2.29.0 | Documentation Sync: API_SPECIFICATION.md & DATABASE_DESIGN.md (Priority #4) |
| `3feb128` | 2.30.0 | Fix: Orders/Production/Installation/Finance List Endpoints Never Actually Paginated |
| `bb2ed5a` | 2.31.0 | Add Purchasing module: Suppliers, Purchase Orders, and receiving |
| `3168764` | 2.32.0 | Marketing Module: campaigns with real lead attribution and revenue performance |
| `797aa57` | 2.33.0 | Customer Portal: separate customer auth identity + self-service access |

---

## 8. Remaining Issues

Re-verified against the current code in this session (not just carried forward from the old audit text):

| # | Issue | Status | Evidence |
|---|---|---|---|
| B1 | Finance invoice list / Production work-order list still have **no `sort` parameter** | ✅ **Resolved in §9 (v2.36.0)** | Was still open as of this report; closed by Phase 17 |
| B6 | Customer archive still has **no restore path** | ✅ **Resolved in §9 (v2.36.0)** | Was still open as of this report; closed by Phase 17 |
| — | **No committed ESLint config** | ✅ **Resolved in §9 (v2.36.0)** | Was still open as of this report; closed by Phase 17 |
| S4 | CORS `allow_methods`/`allow_headers` still wildcarded (`["*"]`) | **Still open** | `backend/core/bootstrap/app_factory.py:63-64` — out of Phase 17's scope, on `MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 18 (Security & Compliance Hardening) |
| S3 | Auth tokens still stored in `localStorage` | **Still open, and scope widened** | Staff (`frontend/lib/session.ts`) unchanged; the new Customer Portal (`lib/portal-session.ts`) uses the same localStorage pattern, deliberately mirroring staff auth rather than fixing it — out of Phase 17's scope, on Phase 18 |
| S5 | No frontend-only permission-gating hook (`usePermission()`) | 🟡 **Partially resolved in §9 (v2.36.0)** | `lib/permissions.ts`'s `hasPermission()`/`usePermission()` now exists and is applied to the Customers list/detail page as the demonstrated pattern; a platform-wide rollout to every write control remains open |
| S1 | Postgres Row-Level Security (defense-in-depth layer) | **Still not implemented** | Confirmed by the v2.29.0 `DATABASE_DESIGN.md` rewrite itself — explicitly documented as absent, not silently dropped; out of Phase 17's scope, on Phase 18 |
| — | Mobile client (Phase 9) | **Not started** | Untouched in this window; scoped to `MASTER_DEVELOPMENT_ROADMAP.md` Phase 25 |

**Not addressed in this window** (none of these were in the audit's top-5 priority list, so their absence is consistent with the audit's own prioritization, not a miss):
- Item 6 from the original priority list (B1 + B6) — explicitly named as "long-standing, keeps resurfacing" but not picked up this round.
- Item 7 (ESLint config).
- Item 9 (CORS tightening, mobile-nav focus trap, RLS, localStorage→httpOnly-cookie migration, permission-gating hook) — none of this lower-priority hardening was touched.

**Net effect of this window:** all 5 numbered audit priorities are now closed, and the original 10-module ERP roadmap is complete (Purchasing and Marketing were the last two), plus one new beyond-scope module (Customer Portal) shipped. The previously-identified lower-priority hardening backlog and the two recurring deferred bugs remain exactly where the audit left them — nothing regressed, but nothing on that specific list moved either.

---

## 9. Addendum — Phase 17: Stabilization & Technical Debt Closeout (Version 2.36.0)

_Added 2026-07-22, same day as the original report above, after `MASTER_DEVELOPMENT_ROADMAP.md` was introduced and its Phase 17 was executed in full. Covers HEAD commit at time of writing (post-`8fc6506`/Version 2.35.0), i.e. everything not already covered by §1–8 above or by `STONE_WORKFLOW_REPORT.md`._

### 9.1 Theme

`MASTER_DEVELOPMENT_ROADMAP.md` Part 3 opened with Phase 17 specifically because every one of its eight items — B1, B6, the ESLint gap, B7 (dead `module_permissions`), B5 (circular FK), the tablet breakpoint gap, the mobile-nav focus-trap gap, and the icon-library deviation — had already been independently re-identified across two or more prior audit passes (`RELEASE_CHECKLIST.md`, `PROJECT_AUDIT.md`, this document's own §8) without being picked up. This addendum closes all eight in one pass.

### 9.2 Features Added / Fixed

- **Customer archive restore (B6)** — `RestoreCustomerUseCase`, `POST /api/v1/crm/customers/{id}/restore` (`crm:customers:write`, `409` on a not-archived customer), a new `CustomerRestored` event and `CustomerNotArchivedError` exception. Frontend: a Restore action on the Customer detail page and a per-row quick-restore action in the Customers list.
- **Finance/Production `sort` parameters (B1)** — `InvoiceRepository.list()` and `WorkOrderRepository.list()` both gained the same whitelisted-column `_SORTABLE` map + `sort` kwarg `OrderRepository.list()` already established. Frontend: `SortableHeader` columns on both list pages.
- **Committed, CI-enforced ESLint (the "No committed ESLint config" item)** — `eslint@9` + `eslint-config-next@15.5.19` + `@eslint/eslintrc`, a flat `eslint.config.mjs`, and a new `Lint` step in `.github/workflows/ci.yml`. Running it for the first time surfaced 93 pre-existing violations (89 identical `t(x as any)` i18n-key casts, 4 genuine free-form-JSON `any` usages, plus several unused imports/variables and one `jsx-a11y` issue) — all genuinely fixed, none suppressed via rule downgrades or `eslint-disable` comments. `npm run lint` now exits clean.
- **`module_permissions` (B7)** — `lib/permissions.ts` (`hasPermission()`/`usePermission()`) decodes the access token's `role`/`module_permissions` claims and replicates `core/rbac/permissions.py`'s role-rank + action-suffix logic client-side, then gates the Customers list (Create, bulk actions, per-row Restore) and detail page (Archive/Restore) as the demonstrated pattern — the same UX gap named as S5 in §8 above, now partially closed (see the updated §8 table).
- **Circular FK (B5)** — `crm_customers.primary_contact_id`'s `ForeignKey` gained `use_alter=True, name="fk_crm_customers_primary_contact_id"`. `alembic check` confirmed no migration was actually required — this was a metadata/table-sort fix only, verified by a new regression test asserting `Base.metadata.sorted_tables` raises no `SAWarning`.
- **Tablet breakpoint** — a new `NavIconRail` component gives `AppShell` a third responsive tier (persistent icon-only sidebar at 768–1023px), replacing the previous fallback to the phone-width slide-over drawer at that width.
- **Mobile nav focus trap** — a new `useFocusTrap` hook (`lib/use-outside-click.ts`) traps `Tab`/`Shift+Tab` inside the open mobile drawer and restores focus to the trigger on close.
- **Icon library** — `lucide-react` adopted; all 9 hand-rolled inline `<svg>` icons across `app-shell.tsx`, `theme-toggle.tsx`, `company-switcher.tsx`, `language-switcher.tsx`, `quick-create-menu.tsx`, and `ui/data-table.tsx` replaced with the equivalent Lucide component.

### 9.3 Tests Added

**11 new backend tests: 695 → 706 passing.**

| Area | New tests |
|---|---|
| Customer restore (`tests/crm/test_customers_api.py`) | 5 — success, not-archived conflict, not-found, permission-denied, audit-log verification |
| Finance invoice sort (`tests/finance/test_invoices.py`) | 2 — ascending/descending by `invoice_number`, unwhitelisted-column fallback |
| Production work-order sort (`tests/production/test_work_orders.py`) | 2 — ascending/descending by `work_order_number`, sort by `priority` |
| Database schema (`tests/test_database_schema.py`, new file) | 2 — no circular-FK `SAWarning` across the full 14-module table set, `use_alter`/constraint-name pinned |

No frontend unit-test framework exists in this codebase (Playwright e2e only, per §5 of the original report); the frontend changes in this addendum were verified via `tsc --noEmit`, `npm run lint`, and a full production build (all passing), consistent with how every other frontend-only change in this project's history has been verified.

### 9.4 Verification

Full backend suite passing (706/706), `lint-imports` passing (1 contract kept, 0 broken), `alembic check` clean, frontend `tsc --noEmit` clean, `npm run lint` clean (0 errors, 0 warnings), frontend production build clean (68 routes, unchanged count — no new pages, a stabilization pass).

### 9.5 Remaining Issues (re-verified, current as of this addendum)

| # | Issue | Status |
|---|---|---|
| S4 | CORS `allow_methods`/`allow_headers` wildcarded | Still open — `MASTER_DEVELOPMENT_ROADMAP.md` Phase 18 |
| S3 | Auth tokens in `localStorage` (staff + Customer Portal) | Still open — Phase 18 |
| S5 | Frontend permission gating | Partially closed — the utility exists and is demonstrated on one surface; platform-wide rollout still open |
| S1 | Postgres Row-Level Security | Still not implemented — Phase 18 |
| — | Mobile client | Not started — Phase 25 |

Full detail, evidence, and the complete list of files changed is in `PHASE17_COMPLETION_REPORT.md`.
