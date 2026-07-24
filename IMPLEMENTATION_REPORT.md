# G-STONE ERP — Implementation Report

_Date: 2026-07-22 (original report), addended 2026-07-22 (Version 2.36.0 / Phase 17), addended again 2026-07-23 (Version 2.37.0 / Phase 18), addended again 2026-07-23 (Version 2.38.0 / Phase 19), addended again 2026-07-24 (Version 2.39.0 / Phase 20), addended again 2026-07-24 (Version 2.40.0 / Phase 21), addended again 2026-07-24 (Version 2.42.0 / Phase 21 follow-through)_
_Scope: everything implemented since the last audit (`PROJECT_AUDIT.md`, dated 2026-07-21, frozen at commit `521428e` / Version 2.25.0), through current HEAD (Version 2.42.0). Sections 1–8 below are the original report, kept as written — they describe what was true at the time. §9 is a same-day addendum covering Phase 17 (Version 2.36.0); §10 covers Phase 18 (Version 2.37.0); §11 covers Phase 19 (Version 2.38.0), closing the eight gaps `STONE_WORKFLOW_REPORT.md` §12 deliberately deferred from Phases 1–2; §12 covers Phase 20 (Version 2.39.0), extending the Cut Optimization engine and closing Sprint 2's deferred supplier-catalog-import gap; §13 covers Phase 21 (Version 2.40.0), giving the AI Sales Assistant its first real model behind the existing provider abstraction; §14 covers Phase 21's own follow-through (Version 2.42.0), closing the two product surfaces §13 deliberately deferred. Corrections are recorded as annotations on prior sections rather than silent rewrites, consistent with this project's practice. (Versions 2.34.0 and 2.35.0, the two Stone Fabrication Workflow phases, are covered by their own dedicated `STONE_WORKFLOW_REPORT.md`, not repeated here.)_
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

---

## 10. Addendum — Phase 18: Security & Compliance Hardening (Version 2.37.0)

_Added 2026-07-23, after `MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 18 was executed in full. Covers HEAD commit at time of writing (post-`bdb80b6`/Version 2.36.0)._

### 10.1 Theme

Every item in this addendum closes a gap §8/§9.5 above explicitly named as "Still open — Phase 18": S4 (CORS wildcards), S3 (localStorage tokens), S5 (frontend permission gating — this addendum finishes the platform-wide rollout §9.5 left open), and S1 (Postgres RLS). Two items go beyond what §8/§9.5 tracked, both named in `MASTER_DEVELOPMENT_ROADMAP.md` Phase 18 itself: staff MFA, and a compliance audit-log export/retention admin surface.

### 10.2 Features Added / Fixed

- **Postgres Row-Level Security (S1)** — migration `55d19b5b6862` enables RLS + a `company_isolation` policy on all 75 tenant-owned tables. A new `CompanyContextMiddleware` (`core/api/middleware.py`) plus a SQLAlchemy `after_begin` hook (`core/db/session.py`) populate the `app.current_company_id` session variable automatically per request — zero router/repository changes needed. No-ops on SQLite. See `DATABASE_DESIGN.md` §17.
- **httpOnly cookie auth (S3)** — staff (`core/auth/router.py`) and Customer Portal (`modules/customer_portal/presentation/api/auth.py`) both now set httpOnly/`Secure`/`SameSite=Lax` cookies on login/select-company/refresh, in addition to the unchanged JSON body (kept for Bearer-token clients). `core/rbac/dependencies.py` and `get_current_customer` accept either transport. Frontend (`lib/api-client.ts`, `lib/portal-api-client.ts`, `lib/session.ts`, `lib/portal-session.ts`) rewritten to authenticate via the cookie exclusively and never persist a raw token — only a non-sensitive session-active flag and (staff) the `role`/`module_permissions`/`active_company_id` claims, now also returned as plain response fields since an httpOnly token's claims aren't client-readable.
- **CORS tightening (S4)** — `core/config.py` gained explicit `cors_allow_methods`/`cors_allow_headers` settings; `core/bootstrap/app_factory.py` no longer passes `["*"]` for either.
- **Frontend permission gating, platform-wide rollout (S5)** — the `usePermission()` pattern §9.2 demonstrated on Customers only is now applied to 32 more files spanning every module with a write action (Leads, Tasks, Catalog, Sales Projects/Quotes, Orders, Production, Installation, Finance, Purchasing, Marketing, Communication, Cut Optimization, Dashboard) — full list and per-file permission string in `CHANGELOG.md` [2.37.0].
- **Staff MFA (new)** — TOTP via `pyotp` (`core/auth/mfa.py`), `POST /auth/mfa/{setup,enable,disable,verify}`, a login-time `{mfa_required, mfa_token}` challenge/response flow, and a per-company `mfa_required_roles` policy enforced at `/auth/select-company`. Frontend: a login MFA-code step and a new `/settings/security` page.
- **Compliance audit-log export/retention (new)** — `core/audit/router.py` (owner-only, `core:audit:export`): filterable/paginated log listing, CSV export, retention-policy get/set, manual purge. New `audit_retention_policies` table. Frontend: a new `/settings/audit-log` page.

### 10.3 Tests Added

**16 new backend tests: 706 → 722 passing** (`tests/test_phase18_security_hardening.py`).

| Area | New tests |
|---|---|
| httpOnly cookie auth | 5 — login sets cookies, `/auth/me` authenticates via cookie alone (no header), select-company response carries claims, cookie-only refresh with no body, logout clears cookies + revokes |
| Staff MFA | 5 — setup→enable→login-challenge→verify round trip, wrong-code rejection, disable requires a valid code, per-company-per-role enforcement (blocked, then unblocked once enabled) |
| Audit log export/retention | 5 — list/export reflect a real audited write, retention policy defaults to "forever" then can be set, purge without a policy is rejected (`422`), purge deletes only entries older than the window, non-owner gets `403` |
| CORS | 1 — settings no longer wildcard methods/headers |

No frontend unit-test framework exists in this codebase (consistent with §5/§9.3); frontend changes verified via `tsc --noEmit`, `npm run lint`, and a full production build.

### 10.4 Verification

Full backend suite passing (722/722), migrations round-trip clean (`upgrade head` → `downgrade -2` → `upgrade head` against a scratch SQLite database), frontend `tsc --noEmit` clean, `npm run lint` clean (0 errors, 0 warnings), frontend production build clean (61 routes, +2 new: `/settings/security`, `/settings/audit-log`).

### 10.5 Remaining Issues (re-verified, current as of this addendum)

| # | Issue | Status |
|---|---|---|
| — | RLS full efficacy in production | Policy + wiring shipped; requires the app's runtime Postgres role to be a non-owner role (infra step, not yet executed) — see `DATABASE_DESIGN.md` §17 |
| — | Per-session/device token revocation | `token_denylist.py`'s generation-counter design remains all-or-nothing ("logout everywhere"); a "revoke this one session" feature would need a new per-JTI denylist — not attempted this phase |
| — | Real AI provider, payments, mobile client | Not started — `MASTER_DEVELOPMENT_ROADMAP.md` Phases 21/22/25 |

Full detail is in `CHANGELOG.md` [2.37.0].

---

## 11. Addendum — Phase 19: Stone Fabrication Workflow, Phase 3 (Version 2.38.0)

_Added 2026-07-23, after `MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 19 was executed in full. Covers HEAD commit at time of writing (post-Phase 18/Version 2.37.0)._

### 11.1 Theme

`STONE_WORKFLOW_REPORT.md` §12 named eight items as deliberate, deferred gaps in Phases 1–2 (Versions 2.34.0/2.35.0): a reservation UI outside the Production Job page, drag-and-drop stage movement, stage reordering UI, priority/stage-change notifications, bulk operations, finer-grained production permissions, offcut dimension validation, and the sold-vs-consumed status ambiguity. This addendum closes all eight in one pass, the same "close everything a prior phase deliberately deferred, in one dedicated pass" shape as Phase 17 (§9) and Phase 18 (§10).

### 11.2 Features Added / Fixed

- **Reservation UI** — `/catalog/slabs` gained checkbox-based multi-select (available slabs only) + a bulk "Reserve selected" toolbar; a new `/catalog/reservations` page browses every reservation company-wide (not just per-order) with status filtering and a Release action; `/orders/{id}` gained a "Reserved Slabs" card. Backend: `GET /catalog/reservations`'s `order_id` query param became optional (previously required) and the endpoint gained cursor pagination + a `status` filter — the same endpoint now serves both the original per-order view and the new company-wide browse.
- **Drag-and-drop stage movement** — `/reports/production-planning`'s Kanban board gained native HTML5 drag-and-drop (job card → stage column) plus a checkbox multi-select + "Move selected to stage" bulk toolbar, both calling the existing `POST /production/{id}/stage` endpoint.
- **Stage reordering UI** — `/production/stages` gained move-up/move-down buttons, swapping `sort_order` between adjacent stages via two `PATCH` calls — no new backend endpoint needed, `sort_order` was already settable, just never exposed.
- **Priority/stage-change notifications** — new `production_notifications` table + `notify_user` helper (mirrors `modules/installation/application/notification_helper.py`'s `notify_crew` exactly), wired into `UpdateWorkOrderPriorityUseCase` (fires on a change to `urgent` with an assigned operator), `UpdateWorkOrderStageUseCase` (fires on any stage change with an assigned operator — deliberately not keyed to a specific stage name, since `production_stages.name` is per-company configurable), and `AssignWorkOrderOperatorUseCase` (fires on a new assignment). New `GET/POST /production/notifications` endpoints mirror Installation's shape exactly. Frontend: a third notification source merged into the Dashboard's existing task/installation notification feed.
- **Bulk operations** — confirmed there is no backend "bulk endpoint" pattern anywhere in this codebase (Customers' Phase 9 bulk actions are pure frontend `Promise.allSettled` fan-outs over single-item endpoints); both new bulk flows (reserve multiple slabs, move multiple jobs to a stage) follow that exact same convention rather than introducing a new backend pattern.
- **Finer-grained production permissions** — `production:priority:write`/`production:operator:write`/`production:stage:write` added alongside (not replacing) `production:write`, applied to the three specific tracking endpoints. Additive: default role-rank behavior is unchanged (the action suffix is still `write`), but `module_permissions` overrides can now grant one of the three independently.
- **Offcut dimension/area validation** — `CreateOffcutUseCase` now checks the offcut's `length_mm`/`width_mm` against the parent slab's own recorded dimensions in both orientations before creating it, raising a new `OffcutTooLargeError` (422) when it couldn't plausibly fit. Silently skipped when either slab is missing a dimension.
- **`sold` vs. `consumed` reconciliation** — `consumed` is now reachable only via Production's own completion cascade (`UpdateSlabStatusInput.system_triggered`, defaulted `False`, set `True` only inside `work_order_use_cases.py`'s `_cascade_slabs`); a manual PATCH to `consumed` now raises a new `SlabStatusRequiresSystemActionError` (409). `UpdateSlabStatusUseCase` also now auto-releases a slab's dangling active reservation when a user manually transitions it to `sold` or `scrap` — closing the specific "reservation left stuck `active` forever" data-quality gap `STONE_WORKFLOW_REPORT.md` flagged, without changing which transitions are legal (the existing `reserved → sold` test still passes unmodified).

### 11.3 Tests Added

**15 new backend tests: 722 → 737 passing.**

| Area | New tests |
|---|---|
| Offcut validation (`tests/catalog/test_phase19_offcut_validation_and_status_boundary.py`) | 3 — too-large rejected, fits-when-rotated accepted, no-dimensions-on-file skips validation |
| Sold/consumed boundary (same file) | 3 — manual PATCH to `consumed` rejected, selling a reserved slab releases its reservation, scrapping an in-production slab releases its reservation |
| Company-wide reservation browsing (same file) | 2 — `order_id`-omitted lists the whole company, `status` filter works |
| Finer-grained permissions (`tests/production/test_phase19_permissions_and_notifications.py`) | 2 — viewer rejected from all three endpoints by default, a targeted `module_permissions` override grants exactly one of the three |
| Notifications (same file) | 5 — urgent-priority-with-operator notifies, priority-change-without-operator notifies no one, operator assignment notifies, stage change notifies, mark-read + `unread_only` filter |

No frontend unit-test framework exists in this codebase (consistent with §5/§9.3/§10.3); frontend changes verified via `tsc --noEmit`, `npm run lint`, and a full production build.

### 11.4 Verification

Full backend suite passing (737/737), migrations round-trip clean (`upgrade head` → `downgrade -1` → `upgrade head` against a scratch SQLite database), frontend `tsc --noEmit` clean, `npm run lint` clean (0 errors, 0 warnings), frontend production build clean (60 routes, +1 new: `/catalog/reservations`).

### 11.5 Remaining Issues (re-verified, current as of this addendum)

| # | Issue | Status |
|---|---|---|
| — | RLS full efficacy in production (non-owner runtime DB role) | Still open — infra step, tracked since Phase 18 (§10.5) |
| — | Per-session/device token revocation | Still open — tracked since Phase 18 (§10.5) |
| — | Multi-slab/cross-job batch optimization, CNC export, supplier catalog import | ✅ Closed this window — see §12 below |
| — | Real AI provider, payments, mobile client | Not started — Phases 21/22/25 |

Full detail is in `CHANGELOG.md` [2.38.0].

---

## 12. Addendum — Phase 20: Advanced Cut Optimization & Supply Chain Intelligence (Version 2.39.0)

_Added 2026-07-24, after `MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 20 was executed in full. Covers HEAD commit at time of writing (post-Phase 19/Version 2.38.0)._

### 12.1 Theme

`MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 20 named four items extending the Cut Optimization engine (Version 2.35.0) and the wider supply chain into a shop-floor and procurement automation layer: multi-slab/cross-job batch optimization, CNC/machine-ready export, automated low-stock → purchase suggestions, and a standardized supplier catalog import pipeline (the last one closing a gap Sprint 2/Phase 9 deliberately deferred). This addendum closes all four in one pass.

### 12.2 Features Added

- **Multi-slab / cross-job batch optimization** — `POST /cut_optimization/batch-runs` (`modules/cut_optimization/application/use_cases/run_batch_optimization_use_case.py`). A new `pack_pieces_multi_slab` outer bin-packing orchestrator (`domain/batch_cutting_algorithm.py`) reuses the existing single-slab `pack_pieces` engine (`cutting_algorithm.py`, left completely unmodified) as its inner per-slab packer: given an ordered list of candidate slabs and one combined pool of pieces, it fills slabs in order, carrying whatever didn't fit forward to the next slab, until every piece is placed or the slab list is exhausted. Pieces from multiple jobs/work orders are simply concatenated into one list, distinguished only by a `label` prefix convention (e.g. `"WO-1024: Countertop A"`) — reuses an existing free-text extension point rather than threading a new field through the single-slab engine every other use case depends on. Without explicit `slab_ids`, candidate slabs are auto-selected via a new `SlabRepository.list_available_for_material` (every `available` slab/offcut for the material, smallest-area-first, up to `max_slabs`) — the same "spend the smallest usable piece of inventory first" preference Smart Offcut Management already applies to one job. Persisted to a new `cut_optimization_batch_runs` table (a sibling to, not an extension of, `cut_optimization_runs`; see `DATABASE_DESIGN.md` §16.2). Frontend: `/cut-optimization/batch` (create + per-slab `SlabLayoutSvg` breakdown), `/cut-optimization/batch/history` (list), `/cut-optimization/batch/history/{id}` (reopen).
- **CNC/machine-ready export** — `domain/dxf_export.py` converts a persisted run's real-millimeter `placements` (plus, for a batch run, `slabs`) into a DXF file via `ezdxf` (R2010, `SLAB`/`CUT`/`LABELS` layers) — the same coordinate data the SVG visualization already renders, just handed to a CAM-ready format. `GET /cut_optimization/runs/{id}/export.dxf` and `GET /cut_optimization/batch-runs/{id}/export.dxf`; a batch run's DXF lays every used slab side by side with a fixed gap, matching placements to their slab by `slab_ref`. "Export DXF" buttons added to every existing single-run page (`/cut-optimization`, `/cut-optimization/history/{id}`) and the new batch pages, via a new `apiDownload`-based `exportRunDxf`/`exportBatchRunDxf` pair in `lib/api/cut-optimization.ts`.
- **Automated low-stock → purchase suggestion** — `GET /reports/inventory/low-stock` (`LowStockPurchaseSuggestionsUseCase`, `ReportsRepository.low_stock_materials`). Flags an active material when it has `stock_threshold` (default 3) or fewer `available` slabs, or when Smart Offcut Management has recorded `no_fit_threshold` (default 3) or more `no_suitable_offcut` outcomes for it within `no_fit_window_days` (default 30) — read directly off existing `offcut_recommendation.computed` audit-log entries (`RecommendOffcutsUseCase._audit`), no new counter table needed since every recommendation call already wrote that row, it was just never queried before. Deliberately read-only: the new "Low-Stock Purchase Suggestions" card on `/reports/inventory` links each flagged row into Purchasing's own `/purchasing/orders/new?material_id=...&description=...` (a new lightweight `window.location.search` prefill on that page, avoiding a `useSearchParams`/Suspense-boundary requirement for a one-time prefill), keeping the write action inside Purchasing's module boundary rather than Reports reaching into it.
- **Standardized supplier catalog import** — `POST /catalog/materials/import` (multipart CSV) and `GET /catalog/materials/import/template` (starter CSV), backed by `ImportSupplierCatalogUseCase`. One row per material: Brand and Material are found-by-name (case-insensitive, new `BrandRepository.get_by_name`/`MaterialRepository.get_by_brand_and_name`) or created; `thicknesses_mm`/`sizes` are `;`-separated lists appended to that material's existing option lists (skipping values already present, so re-importing the same file is idempotent). Best-effort per row — a bad row (missing brand/material name) is caught, recorded in the response's `errors: [{row_number, message}]`, and the rest of the file still imports; consistent with this being a bulk import where a partial success telling the user exactly which rows to fix beats an all-or-nothing failure. Frontend: `/catalog/materials/import` (template download, upload, results summary), linked from `/catalog/materials`.

### 12.3 Tests Added

**21 new backend tests: 737 → 758 passing.**

| Area | New tests |
|---|---|
| Batch optimization (`tests/cut_optimization/test_batch_optimization_api.py`) | 11 — explicit `slab_ids` nests across both slabs, auto-select prefers the smaller slab first, unplaced pieces reported when they exceed all candidate slabs, `422` with no available slabs, `422` with zero pieces, list/reopen history, unknown-id `404`, company isolation, single-run DXF export (content-type + DXF markers), unknown-run DXF export `404`, batch-run DXF export (slab ref appears in the file) |
| Supplier catalog import (`tests/catalog/test_supplier_catalog_import.py`) | 6 — template download, create-brand-and-material-with-options, re-import upserts without duplicating, row errors reported without aborting the rest of the file, missing required columns → `400`, viewer role rejected (`403`) |
| Low-stock suggestions (`tests/reports/test_low_stock_suggestions.py`) | 4 — zero-stock material flagged, well-stocked material excluded at a `0` threshold, a configurable higher threshold flags it anyway, empty company returns no suggestions |

No frontend unit-test framework exists in this codebase (consistent with §5/§9.3/§10.3/§11.3); frontend changes verified via `tsc --noEmit`, `npm run lint`, and a full production build.

### 12.4 Verification

Full backend suite passing (758/758), `lint-imports` clean, migrations round-trip clean (`upgrade head` → `downgrade -1` → `upgrade head` against a scratch SQLite database — the new `cut_optimization_batch_runs` table's own migration carries its own Postgres RLS policy directly, per the Phase 18/19 convention), frontend `tsc --noEmit` clean, `npm run lint` clean (0 errors, 0 warnings), frontend production build clean (78 routes, +4 new: `/catalog/materials/import`, `/cut-optimization/batch`, `/cut-optimization/batch/history`, `/cut-optimization/batch/history/{id}`).

### 12.5 Remaining Issues (re-verified, current as of this addendum)

| # | Issue | Status |
|---|---|---|
| — | RLS full efficacy in production (non-owner runtime DB role) | Still open — infra step, tracked since Phase 18 (§10.5) |
| — | Per-session/device token revocation | Still open — tracked since Phase 18 (§10.5) |
| — | Batch optimization runs synchronously in the request/response cycle | A large batch (many jobs, many slabs) has no queue to fall back on yet — tracked as part of Phase 24's background job queue, same ceiling PDF/report generation already has |
| — | Supplier catalog import is CSV-only, no direct manufacturer API integration | Acceptable for now per the roadmap's own scope ("CSV/API"); a real API integration per supplier remains future work if a supplier offers one |
| — | Real AI provider, payments, mobile client | Real AI provider ✅ closed — see §13 below; payments/mobile still Phases 22/25 |

Full detail is in `CHANGELOG.md` [2.39.0].

---

## 13. Addendum — Phase 21: Real AI Provider Integration (Version 2.40.0)

_Added 2026-07-24, after `MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 21 was executed in full. Covers HEAD commit at time of writing (post-Phase 20/Version 2.39.0)._

### 13.1 Theme

The AI Sales Assistant (Phase 5, Version 2.8) was deliberately built provider-agnostic: every provider name (`mock`/`openai`/`anthropic`/`gemini`/`ollama`/`azure_openai`) resolved to `MockAIProvider`, a deterministic heuristic engine — the abstraction was the point of that phase, not a real model. This addendum is the follow-through `MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 21 named, mirroring exactly how Phase 7 followed Phase 4 for Communication: implement a real provider behind the existing interface, add the cost controls a first real per-call cost demands, and give every AI-generated recommendation a genuine audit trail back to the exact prompt/response that produced it — all without touching any use case, DTO, schema, or the frontend's calling convention.

### 13.2 Features Added

- **Real `AnthropicProvider`** (`modules/ai/infrastructure/providers/anthropic_provider.py`) — `anthropic` now resolves to a real implementation calling the Claude Messages API with structured JSON output (`output_config.format`, one JSON Schema per analysis kind), model configurable via `Settings.anthropic_model` (default `claude-opus-4-8`). Each of the four analysis methods asks the model only for the genuinely language/judgment half of its output (lead score/priority/next-best-action/quality explanation; conversation language/intent/sentiment/urgency/summary; which candidate materials to recommend/cross-sell/upsell; task titles/priorities) — exact-id matching (duplicate leads, similar customers, valid task-entity references) and financial-threshold math (margin risk, price anomalies, discount averages, delivery complexity) are computed deterministically by a new shared module, `modules/ai/domain/analysis_helpers.py`, and merged into the model's output before it reaches the unchanged use-case layer. This structurally prevents the two failure modes a real model uniquely introduces: a hallucinated UUID standing in for a duplicate/similar-record match, and an approximated number where the database already has the exact figure. Quote-analysis candidate selection is bounds-checked against the real candidate list the use case already built (`analysis_helpers.select_candidates_by_id`) — a model-selected id outside that set is silently dropped, never fabricated into a row.
- **Registry wiring** (`modules/ai/infrastructure/providers/registry.py`) — `get_provider()` now resolves an omitted `provider_name` via `Settings.ai_default_provider` (default `mock`) instead of the hardcoded `DEFAULT_AI_PROVIDER` constant, so an operator can move every company from mock to the real provider (or back, e.g. during a cost incident) with one environment variable and no redeploy of any calling code.
- **Cost controls** — `_check_usage_allowed` (`modules/ai/application/use_cases/_shared.py`, run before every provider call) enforces, in order: (1) a per-company rate limit (`ai_analysis_rate_limiter`, a `FixedWindowRateLimiter` instance — the exact same class the login endpoint already uses — at 20 requests/minute), then (2) a daily spend cap (`Settings.ai_daily_budget_usd`, default $20, `0` disables it) computed by summing today's real `cost_usd` from the new audit table before the provider is invoked. Both rejections raise a new domain exception (`AIRateLimitedError`/`AIBudgetExceededError`) mapped to HTTP `429`.
- **Prompt/response audit logging** — new `AIProviderCallLog` model/table (`ai_provider_call_logs`, migration `e12a7189e238`) records every call attempt — success, rejection, or upstream failure — with the exact prompt sent, the real provider's raw response text (`null` for mock, which makes no real API call), token counts, computed cost, latency, and any error message. `run_provider()` writes this row for every outcome, committing it immediately on failure (rather than leaving it to the caller's own `db.commit()`, since the use case is about to raise and the request's session would otherwise roll it back along with everything else). `AIRecommendation` gained a nullable `provider_call_id` FK so every recommendation traces back to the exact call that produced it. A new `GET /ai/usage` endpoint (`ai:dashboard:read`, same viewer-tier permission as the existing AI Dashboard) surfaces today's spend/budget/call count and a recent-call-log page; the AI Dashboard UI (`/ai/dashboard`) gained a corresponding "AI Provider Usage & Cost" card, and `RecommendationCard` now shows the recommendation's own `prompt` alongside its `response` in the existing details toggle.
- **Clean error surface** — a new `ServiceUnavailableError` (503) in `core/api/errors.py` covers an unconfigured real provider (no `ANTHROPIC_API_KEY` — `AIProviderNotConfiguredError`) and upstream API failures (`AIProviderUpstreamError` — network failure, authentication rejected upstream, rate-limited upstream, or a response that didn't parse as the expected JSON, including a `stop_reason: "refusal"` response). The four analysis endpoints (`modules/ai/presentation/api/analysis.py`) now share one exception-to-HTTP mapping covering these plus the pre-existing `UnknownAIProviderError` (→ `400`) — previously an unknown provider name fell through to a generic `500` with no translation at all; that gap is closed as a side effect of adding the mapping this phase needed anyway.
- **Preserved invariant, zero new code required** — "AI never performs a business action automatically" needed no change to stay true: `ReviewRecommendationUseCase` was already recommendation-type-agnostic (it only ever updates the recommendation row's own `status`/`edited_response`), so real-provider-generated recommendations flow through the exact same human Accept/Reject/Edit gate with no special-casing.
- **Deliberately deferred at the time, closed in §14**: the roadmap's own "natural scope expansion once a real model exists" examples (AI-drafted quote line-item suggestions, AI-drafted Communication Center reply drafts) were new product surfaces — new recommendation types, new use cases, new UI — rather than the provider-integration/cost-control/audit-trail infrastructure this phase's other four bullets named. See §14 (Version 2.42.0) for the completed follow-through.

### 13.3 Tests Added

**16 new backend tests: 758 → 774 passing.**

| Area | New tests |
|---|---|
| `AnthropicProvider` unit tests (`tests/ai/test_anthropic_provider.py`) | 8 — raises when unconfigured, lead analysis merges LLM judgment with deterministic matching, conversation analysis merges extraction/link-suggestion, quote analysis selects only real candidates and drops a hallucinated id, task suggestion drops a task referencing an unknown entity, upstream rate-limit error mapped, invalid JSON response mapped, `refusal` stop reason mapped |
| Cost controls & audit trail (`tests/ai/test_usage_and_cost_controls.py`) | 8 — usage endpoint empty for a fresh company, successful mock analysis logged, unconfigured-anthropic call returns 503 and logs the failure, rate limit rejects the request beyond the per-company window, rate limit is scoped per company, daily budget cap rejects further calls once reached, a `0` budget disables the cap, usage is viewer-tier readable |
| `tests/ai/test_provider_registry.py` | Updated (not net-new) — split the old 5-way parametrized "every real provider slot still resolves to mock" test into a dedicated assertion that `anthropic` now resolves to the real `AnthropicProvider`, plus the same parametrized test for the three still-mock slots (`openai`/`gemini`/`ollama`/`azure_openai`) |

No frontend unit-test framework exists in this codebase (consistent with §5/§9.3/§10.3/§11.3/§12.3); frontend changes verified via `tsc --noEmit`, `npm run lint`, and a full production build.

### 13.4 Verification

Full backend suite passing (774/774), `lint-imports` clean, migrations round-trip clean (`upgrade head` → `downgrade -1` → `upgrade head` against a scratch SQLite database — the new `ai_provider_call_logs` table's own migration carries its own Postgres RLS policy directly, per the Phase 18/19/20 convention, and its `ai_recommendations.provider_call_id` column/FK addition uses Alembic's `batch_alter_table` since SQLite has no native `ALTER TABLE ADD CONSTRAINT`), frontend `tsc --noEmit` clean, `npm run lint` clean (0 errors, 0 warnings), frontend production build clean (78 routes, no new routes this phase — the AI Dashboard page was extended in place, not replaced).

### 13.5 Remaining Issues (re-verified, current as of this addendum)

| # | Issue | Status |
|---|---|---|
| — | RLS full efficacy in production (non-owner runtime DB role) | Still open — infra step, tracked since Phase 18 (§10.5) |
| — | Per-session/device token revocation | Still open — tracked since Phase 18 (§10.5) |
| — | Batch optimization runs synchronously in the request/response cycle | Still open — tracked since Phase 20 (§12.5), part of Phase 24's background job queue |
| — | Rate limiting is in-process only (mirrors the login rate limiter's own documented caveat) | A multi-instance deployment would need the AI analysis rate limit's counter store (and the login rate limiter's) in Redis instead of an in-process dict; tracked as part of Phase 24 |
| — | AI-drafted quote line items / Communication reply drafts | **Closed** — see §14 (Version 2.42.0) |
| — | Payments, mobile client | Not started — Phases 22/25 |

---

## 14. Addendum — Phase 21 Follow-Through: AI Draft Generation (Version 2.42.0)

_Added 2026-07-24, same day as §13. Covers HEAD commit at time of writing (post-Version 2.40.0's Phase 21 core delivery)._

### 14.1 Theme

§13.2 named two "natural scope expansion" examples as deliberately out of scope for Phase 21's core delivery: AI-drafted Quote line items and AI-drafted Communication Center reply drafts. Requested explicitly as a continuation of Phase 21 (not Phase 22), this addendum closes both, behind the exact same `AIProvider` interface Phase 21 established — no new abstraction, no change to how a provider is selected or billed.

### 14.2 Features Added

- **Two new `AIProvider` methods** — `draft_conversation_reply` and `draft_quote_line_items` were added to the abstract base (`modules/ai/infrastructure/providers/base.py`) and implemented in both `MockAIProvider` (`modules/ai/infrastructure/providers/mock_provider.py` — the reply draft reuses `analyze_conversation`'s own language/intent detection as a pure computation, so the two stay consistent by construction) and `AnthropicProvider` (`modules/ai/infrastructure/providers/anthropic_provider.py` — two new JSON schemas, `_REPLY_SCHEMA`/`_QUOTE_DRAFT_SCHEMA`, and a dedicated system prompt for the reply draft that explicitly instructs the model this is a draft a human still sends).
- **Two new recommendation types** (`modules/ai/domain/value_objects.py`) — `suggested_reply` and `quote_draft_line_items` — reuse the existing `ANALYSIS_KIND_CONVERSATION`/`ANALYSIS_KIND_QUOTE` categories and the existing `ai_recommendations` table; no migration needed.
- **`DraftConversationReplyUseCase`** (`modules/ai/application/use_cases/conversation_reply_draft_use_case.py`) — loads a Conversation's last 100 messages (`MessageRepository.list_for_conversation`), calls the provider through the existing `run_provider()` (so rate-limiting, the daily budget cap, and prompt/response audit logging are unchanged), and creates one `suggested_reply` recommendation. `POST /ai/conversations/{id}/draft-reply` (`ai:recommendations:write`, same tier as the other four analysis endpoints).
- **`DraftQuoteLineItemsUseCase`** (`modules/ai/application/use_cases/quote_draft_use_case.py`) — loads a Project's Rooms/Items (`RoomRepository`/`ProjectItemRepository`) and, where the company has a default Price List, each item's sale price (`PriceListRepository`/`PriceListEntryRepository`). The provider supplies only `description` and a bounded `waste_factor_pct` (0–20) per item; `suggested_quantity = base_quantity * (1 + waste_factor_pct / 100)` and `estimated_total = suggested_quantity * unit_sale_price` are always computed in the use case, never trusted from the model, and a returned `project_item_id` outside the real item set is dropped rather than kept. `POST /ai/projects/{id}/draft-quote-items` (`ai:recommendations:write`).
- **Communication inbox UI** (`frontend/app/(app)/communication/inbox/page.tsx`) — a "Draft Reply" button calls the new endpoint and shows the resulting recommendation in the existing AI panel; accepting it copies `draft_reply` into the existing compose box (`setComposerText`) — the same mechanism already used for message templates, so accepting a draft never sends anything by itself.
- **Sales Project detail UI** (`frontend/app/(app)/sales/projects/[id]/page.tsx`) — a new "AI Draft Quote Items" card on the Overview tab calls the new endpoint and renders each `quote_draft_line_items` recommendation via the shared `RecommendationCard` plus a review table (room, item, description, suggested quantity, unit price, estimated total). Reviewing/accepting only ever changes the recommendation's own status — no Quote or `QuoteSectionItem` is created by this flow; creating the actual Quote remains the existing "Create Quote" action on the same page.
- i18n keys added to all three locale files (`draftReply`, `type_suggested_reply`, `draftQuoteItemsTitle`/`draftQuoteItems`/`draftQuoteItemsDesc`, `type_quote_draft_line_items`, and the draft table's column headers).

### 14.3 Tests Added

| Area | New tests |
|---|---|
| `AnthropicProvider` (`tests/ai/test_anthropic_provider.py`, appended) | 3 — reply draft returns text + detected language; a hallucinated `project_item_id` in the quote draft is dropped; an out-of-range `waste_factor_pct` is clamped to 0–20 |
| `tests/ai/test_conversation_reply_draft.py` | 4 — creates a `suggested_reply` recommendation; never creates a real `Message` row; 404 for an unknown conversation; 403 for a viewer-role caller |
| `tests/ai/test_quote_draft.py` | 6 — creates a recommendation with correct deterministic `suggested_quantity`/`estimated_total`; prices are `null` with no default Price List configured; an empty Project (no items) still returns a valid empty draft; never creates a `Quote`; 404 for an unknown project; 403 for a viewer-role caller |

No frontend unit-test framework exists in this codebase (consistent with §5/§9.3/§10.3/§11.3/§12.3/§13.3); frontend changes verified via `tsc --noEmit`, `npm run lint`, and a full production build.

### 14.4 Verification

Full backend suite passing (793/793 — 780 prior + 13 new), `lint-imports` clean (no new module boundary crossed — both new use cases stay inside `modules/ai/`), frontend `tsc --noEmit` clean, `npm run lint` clean, frontend production build clean (66 routes, no new routes this phase — both features extend existing pages in place).

### 14.5 Remaining Issues (re-verified, current as of this addendum)

| # | Issue | Status |
|---|---|---|
| — | RLS full efficacy in production (non-owner runtime DB role) | Still open — infra step, tracked since Phase 18 (§10.5) |
| — | Per-session/device token revocation | Still open — tracked since Phase 18 (§10.5) |
| — | Batch optimization runs synchronously in the request/response cycle | Still open — tracked since Phase 20 (§12.5), part of Phase 24's background job queue |
| — | Rate limiting is in-process only | Still open — tracked since Phase 21 (§13.5), part of Phase 24 |
| — | Payments, mobile client | Not started — Phases 22/25 |

Full detail is in `CHANGELOG.md` [2.40.0].
