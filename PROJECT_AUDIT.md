# G-STONE ERP — Project Audit

_Date: 2026-07-21_
_Scope: full-codebase, read-only audit (`backend/`, `frontend/`, all root design docs) as of commit `521428e` (Version 2.25.0)._
_Method: direct review of all root `*.md` design docs, plus two independent deep-dive passes (backend and frontend) covering module completeness, architecture guardrails, security, performance, database/migration consistency, and doc-vs-code drift. The backend pass ran the full `pytest` suite and `alembic check`; the frontend pass ran `tsc --noEmit` and `next build`._

This is not this project's first audit. `RELEASE_CHECKLIST.md` (2026-06-30, re-audited 2026-07-07), `PRODUCTION_READINESS_REPORT.md` (2026-07-08), and per-version notes in `CHANGELOG.md` already document a strong internal audit culture — most historically-found Critical/High issues are genuinely fixed and were re-verified as still-fixed in this pass. This report focuses on **current state as of 2.25.0**, cross-checks old findings for regressions, and surfaces what those prior passes didn't cover (the two newest versions, doc-vs-code drift, and a few gaps prior passes explicitly deferred that are still open).

---

## 1. Current Project Status

**≈90% of the originally-scoped ten-module ERP is built and in daily use**, plus two modules beyond the original scope (Communication Center, AI Sales Assistant). What's not done is well-defined, not vague:

| Dimension | Status |
|---|---|
| Core platform (auth, RBAC, audit, event bus, storage, module registry) | **100%** — complete, frozen since Phase 1 |
| Original 10-module list (`PROJECT_ANALYSIS.md` §2) | **8/10 shipped**: CRM, Sales, Inventory (Stone Catalog), Production, Installation, Finance, Reports, AI. **Not started**: Purchasing, Marketing |
| Modules beyond the original list | Communication Center (+ real channel integrations), Tasks & Reminders — both shipped |
| Mobile client (Phase 9 of `PROJECT_ANALYSIS.md`) | **Not started** — architecture is API-first/mobile-ready by design, but unvalidated by an actual client |
| Frontend UX/design-system maturity | High — dark mode, accessibility baseline, mobile nav, i18n, print layouts all shipped (2.8.1, 2.9.1, 2.9.2/.3, 2.18) |
| Production hardening | High — path traversal, JWT defaults, rate limiting, upload validation, refresh-token revocation all fixed and re-verified in this pass |
| Test coverage | 553/553 backend tests passing (verified by re-running, not just trusting `CHANGELOG.md`); frontend `tsc --noEmit` and `next build` both clean |
| Documentation currency | **Degraded** — see §9. Two of six root docs (`API_SPECIFICATION.md`, `DATABASE_DESIGN.md`) are 5 modules and ~13 versions stale; `README.md` and `ROADMAP.md` are 2 versions stale |

**Bottom line**: the platform is real, tested, and already in production use by G-STONE GALLERY, not a prototype. The gaps are (a) two genuinely unbuilt modules, (b) a handful of specific, previously-identified UX/pagination gaps that only partially got closed, and (c) design-reference documents that stopped being updated several versions ago even though the code kept shipping.

---

## 2. Completed Modules

| Module | Backend | Frontend | Notes |
|---|---|---|---|
| **Core platform** | ✅ | ✅ | Auth, RBAC (owner/manager/rep/viewer), audit log, event bus, storage, module registry |
| **CRM** (Customers, Leads, Tasks & Reminders) | ✅ 25 endpoints / 5 use cases | ✅ | Full CRUD, pipeline, CSV export, manager assignment, type picker |
| **Stone Catalog** (nav-labeled "Inventory" since 2.25.0) | ✅ 36 endpoints / 8 use cases | ✅ | Brands, collections, materials, slabs, warehouses, price lists, thickness/size options |
| **Sales** (Quotes, Projects/Rooms/Items/Measurements/Drawings/Photos) | ✅ 44 endpoints / 11 use cases | ✅ | Largest module; full project workspace workflow (10 tabs) |
| **Orders** | ✅ 9 endpoints | ✅ | Created from accepted quotes; `OrderApproved` event wired |
| **Production** | ✅ 6 endpoints | ✅ | Work orders, slab consumption |
| **Installation** | ✅ 17 endpoints / 4 use cases | ✅ | Scheduling, crews, Kanban, calendar |
| **Finance** | ✅ 12 endpoints / 3 use cases | ✅ | Invoicing, payments, expenses |
| **Reports** | ✅ 7 endpoints / 6 use cases | ✅ | Cross-module analytics (Sales/Production/Installation/Finance/Inventory), PDF/Excel export, executive dashboard |
| **Communication Center** | ✅ 32 endpoints / 6 use cases | ✅ | Real WhatsApp/Instagram/Messenger/SMTP/Twilio/webhook providers (Version 2.9), encrypted credentials, retry queue |
| **AI Sales Assistant** | ✅ 8 endpoints / 7 use cases | ✅ | Lead scoring, conversation/sales/task intelligence; deliberately mock-provider only, human accept/reject required |

All 10 installed modules have complete Domain → Application → Infrastructure → Presentation layering per `CLAUDE.md`'s Clean Architecture rule; `reports` has no `infrastructure/models/` by design (it's a read-only cross-module aggregator, declared via `depends_on`, not an omission).

---

## 3. Missing Modules

| Module | Status | Impact |
|---|---|---|
| **Purchasing** (suppliers, purchase orders, restocking) | Not started | Named in `PROJECT_ANALYSIS.md` and `ROADMAP.md` as the natural next module once restocking becomes the active bottleneck — deliberately deferred, not forgotten, but genuinely absent from the codebase today |
| **Marketing** (campaigns, feeds `LeadCreated`-adjacent events) | Not started | Last of the original 10-module list; `ROADMAP.md` explicitly scopes it out of every version through 2.25.0, pending Sales/CRM data maturity |
| **Mobile client** (Phase 9) | Not started | The API-first/mobile-parity architecture is a design promise, structurally plausible (stateless JWT auth, no server-rendered-only paths), but has never been exercised by an actual mobile client — "mobile-ready" is unvalidated, not proven |

No partially-built or stub modules were found anywhere in the codebase (confirmed by grep for TODO/FIXME/"coming soon" markers across all of `frontend/app/(app)/**`, and by structural review of `backend/modules/`) — every shipped module is a real, complete, tested implementation.

---

## 4. Bugs Found

None of the following are release-blocking; they're real, verifiable defects at Medium/Low severity found during this pass (as distinct from the architecture/security/performance issues in §5–8, which are broader patterns).

| # | Bug | Where | Severity |
|---|---|---|---|
| B1 | `finance` invoice list has **no sort parameter at all** — `InvoiceRepository.list()` (`backend/modules/finance/infrastructure/repositories/invoice_repository.py:30-45`) accepts no `sort` argument; same true for Production's work-order list. This is a previously-identified gap (`RELEASE_CHECKLIST.md` "Medium" list, 2026-07-07) that was never actually closed — re-confirmed still open in this pass by reading the current repository code directly. | Backend | Medium |
| B2 | Dashboard's `Promise.all` fan-out (`frontend/app/(app)/dashboard/page.tsx:107-119`, 11 parallel requests) fails the **entire page** if any single call rejects (e.g. a transient 500 on the new Inventory Analytics call) — no partial/degraded render, just a top-level error string discarding every other successfully-fetched section. | Frontend | Medium-High |
| B3 | Dashboard KPI/stat math is built on collections capped at `limit: 100` (customers, projects, orders, work orders, leads, tasks) with no cursor follow-up — once any collection exceeds 100 rows, dashboard counts (e.g. overdue orders, in-production counts) will **silently under-count** with no indication. | Frontend | Medium-High |
| B4 | 7+ list pages (Orders, Finance Invoices, Finance Expenses, Production, Catalog Brands, Catalog Warehouses, Catalog Price Lists) call their list endpoint with **no `limit` and no pagination UI**, silently capped at the backend's default 25 rows — a company with >25 open orders or invoices (plausible for an active gallery) sees an incomplete list with zero affordance that more records exist. This is the same class of bug fixed for Customers/Leads/Materials in Version 2.19.0 but never extended to these other pages. | Frontend | High |
| B5 | Circular foreign key between `crm_customers.primary_contact_id` and `crm_contacts.customer_id` (`backend/modules/crm/infrastructure/models/customer.py:18`, `contact.py:14`) triggers a SQLAlchemy table-sort warning during `alembic check` ("unresolvable cycles... may raise an error in a future release"). Both columns are nullable so it works today and all 553 tests pass, but it's a live warning against a future SQLAlchemy upgrade. | Backend/DB | Low |
| B6 | Customer **archive has no restore path** — `UpdateCustomerUseCase` never touches `deleted_at`; no restore use case, endpoint, or repository method exists anywhere. Previously investigated and explicitly recorded as a genuine gap (`RELEASE_CHECKLIST.md` follow-up, 2026-07-08); re-confirmed still absent in this pass. | Backend + Frontend | Medium |
| B7 | `module_permissions` is fetched from the auth API (`frontend/lib/api/auth.ts:33`) but never consumed anywhere in the frontend — dead data, harmless but worth removing or wiring up. | Frontend | Low |

---

## 5. Architecture Issues

- **The import-boundary CI gate promised by `PROJECT_ANALYSIS.md` doesn't exist.** §4.3/§7/§10 of the frozen architecture doc state the core/module boundary is "enforced by a CI lint rule... not just a convention" and that CI runs "an automated import-boundary check." In reality: `import-linter` is declared in `pyproject.toml:11-18` but **is not installed** (missing from `requirements.txt`, fails to even run), and **there is no CI pipeline in this repository at all** — no `.github/workflows`, nothing else found. The only thing actually enforcing the core→module boundary today is `backend/tests/test_core_independence.py`, an AST-based pytest test. It works and passes, but it only runs when someone remembers to run `pytest` locally — there is no automated gate stopping a violating PR from merging. **This is a real gap between the frozen architecture document's stated guarantee and what's actually running.** (Medium-High — the mechanism the docs promise as a hard safety net is absent; the fallback that happens to substitute for it is real but not automatic.)
- **Postgres Row-Level Security, the architecture's "defense-in-depth" layer, was not found anywhere in the codebase.** `PROJECT_ANALYSIS.md` §7 and `DATABASE_DESIGN.md` §7 both describe RLS as a second enforcement layer alongside application-level `company_id` scoping. A grep across all of `backend/` for `ROW LEVEL SECURITY` / `CREATE POLICY` / `row_level_security` returns zero hits — no migration, no raw SQL, nothing. The application-layer scoping itself is thorough and was verified extensively (see §8), so this isn't a live data-leak risk today, but the promised second layer is simply not implemented, and the docs don't flag it as deferred. (Medium — matters more as the system scales past "every query was manually reviewed.")
- **Architecture guardrails that *are* real and hold up well**: `core/` genuinely never imports from `modules.*` (verified by direct grep, not just the passing test); `INSTALLED_MODULES` in the registry exactly matches the `modules/` directory; every module has complete Clean Architecture layering; audit-log + event-bus publication is 100% consistent across every committing use case in every module (verified by scripted cross-check, zero exceptions found) — this specific cross-cutting rule from `CLAUDE.md` is genuinely, not just nominally, enforced by convention.
- **Circular FK** between `crm_customers` and `crm_contacts` (see B5) is a minor architectural smell — a design that predates the later, more structured `sales_project_items`-style patterns.

---

## 6. Database Issues

- **Migrations are in sync**: `alembic check` reports no drift between models and the latest migration head (`4cbc1f1d4028`); single linear 18-migration chain, no branches. All 9 modules with model packages are correctly imported in both `migrations/env.py` and `tests/conftest.py`.
- **Indexes are solid on the paths checked**: `company_id` indexed on every tenant table; a dedicated migration (`e042f8386f09`) adds the composite `(company_id, status)` / `(company_id, lead_source)` indexes matching actual query filter patterns on `crm_customers`/`crm_leads`.
- **Circular FK** (B5 above) — nullable-column workaround holds today, flagged for future SQLAlchemy compatibility.
- **RLS not implemented** — see §5. `DATABASE_DESIGN.md` §7 documents an RLS strategy that doesn't exist in any migration.
- **`DATABASE_DESIGN.md` is materially out of date** — see §9. Four modules' real, migrated, tested schemas (Orders, Production, Installation, Finance) are still described in the doc as "conceptual — not migrated" placeholder sketches that don't match the real column lists.

---

## 7. Frontend Issues

_(Full detail in §4's bugs B2–B4, B7; this section covers non-bug quality findings.)_

- **No ESLint configuration is committed** — `next lint` hangs waiting for interactive setup (no `.eslintrc*`/`eslint.config.*` in `frontend/`), despite `npm run lint` being documented as a standard command in `CLAUDE.md`. `tsc --noEmit` is effectively the only automated static check that actually runs; a real ESLint config (react-hooks rules, unused-vars, etc.) is not enforced anywhere. (Medium)
- **Icon usage deviates from `UI_UX_GUIDELINES.md` §2**, which specifies "a single consistent icon library (e.g., Lucide) used everywhere." The sidebar and 7 other components use hand-drawn inline SVGs instead, explicitly justified in code comments as avoiding "a real design-system decision." Internally consistent in style, but a literal deviation from the written guideline, and now 8 call sites deep — adopting a real icon library later means touching all 8. (Medium)
- **Tablet breakpoint (768–1023px) doesn't match the spec.** `UI_UX_GUIDELINES.md` §7 calls for an icon-only collapsed sidebar at tablet width; the actual implementation (`app-shell.tsx`) gives tablet the same full slide-over hamburger menu as phones — confirmed still true as of 2.25.0, a previously-documented and still-open gap.
- **Mobile nav slide-over has no focus trap** — Escape-to-close and backdrop-click work, but keyboard Tab can escape into the page content behind the open drawer. (Low-Medium, accessibility)
- **Auth tokens in `localStorage`** (`frontend/lib/session.ts`) — both access and refresh tokens, with an XSS-exfiltration exposure the code itself acknowledges in a comment as intentional Phase-2 scope pending a future httpOnly-cookie hardening pass. Not a new finding, but worth carrying forward as accepted (not resolved) tech debt. (Medium/High exposure, low urgency given no known XSS vector currently present)
- **Frontend-only permission gating remains unbuilt** (still true as of this pass) — a viewer-role user sees the same Create/Edit/Archive buttons as an owner and gets a real 403 on submit rather than a hidden/disabled control. Correctly, this is not a security hole (backend RBAC is authoritative and was verified thorough — see §8), but it is a real, still-open UX gap first flagged in `RELEASE_CHECKLIST.md`.
- **What's genuinely solid**: i18n key parity is exact (1225/1225/1225 keys across az/ru/en, verified by script, not sampling); `tsc --noEmit` and `next build` both clean with exactly the 39 routes `CHANGELOG.md` claims; no hardcoded English strings found in the newest (2.24.0/2.25.0) files; `dangerouslySetInnerHTML` has exactly one use and it's a static script with no user input; `SalesSectionTabs` fully replaced the old per-page tab bars with zero leftover duplication; bundle sizes are unremarkable (119–161 kB first load across all routes); heavy dashboard derived-data computation is consistently `useMemo`-wrapped.

---

## 8. Backend Issues

- **Documentation drift is the single biggest backend-side issue** — see §9.
- **No CI pipeline** and a **non-functional import-linter contract** — see §5.
- Everything else checked came back clean or only Low-severity:
  - **SQL injection**: zero risk found — no string-formatted SQL anywhere in `backend/`, 100% SQLAlchemy Core/ORM `select()`.
  - **RBAC on write endpoints**: every `POST`/`PUT`/`PATCH`/`DELETE` across all 10 modules requires `require_permission(...)`, except 3 inbound webhook receivers (Meta/Twilio/generic) — correctly and intentionally public, authenticated instead by per-provider signature verification, exactly as `CLAUDE.md` prescribes.
  - **Company-id scoping**: every `get`/`get_by_id` repository method checked across crm/sales/finance/production (11 repositories, dozens of methods) consistently filters by `company_id`; the one exception (`ChannelRepository.get_by_id_any_company()`) is a documented, justified special case used only by the pre-authentication webhook path.
  - **N+1 queries**: none found — the codebase deliberately avoids ORM `relationship()` lazy-loading in favor of explicit `select()` statements, which eliminates the classic pattern by construction.
  - **New Version 2.25.0 code** (`GET /api/v1/reports/inventory`) is correctly RBAC-gated and company-scoped end-to-end through its use case and repository calls — no regression in the newest, least-audited code.
  - **Hardcoded secrets**: none outside the documented seed script credential.
  - **Audit log + event bus discipline**: 100% consistent — every use case that commits a write also records an audit entry and publishes an event, verified by scripted cross-check across all modules, zero exceptions.

---

## 9. Security Issues

| # | Issue | Severity | Status |
|---|---|---|---|
| S1 | Postgres Row-Level Security (the architecture's documented defense-in-depth layer) is not implemented anywhere | Medium | Open, undocumented as a gap |
| S2 | No CI-enforced import-boundary check; `import-linter` declared but not installed/runnable | Medium | Open |
| S3 | Auth tokens (access + refresh) stored in `localStorage`, exposed to XSS exfiltration | Medium/High exposure, Low urgency | Open, acknowledged in code as accepted Phase-2 tech debt |
| S4 | CORS `allow_methods`/`allow_headers` wildcarded (`["*"]`) — origins are correctly restricted and environment-configurable, so actual exposure is low, but tightening these to explicit lists is cheap hardening | Low | Open |
| S5 | No frontend-only permission gating (viewer role sees write UI it can't use) | Low (UX, not a real security hole — backend RBAC is authoritative and verified solid) | Open, previously documented |
| S6 | Path traversal (upload), insecure JWT default, missing rate limiting, missing upload size/type limits, missing RBAC on document upload | — | **All previously fixed and re-verified still fixed in this pass** — no regressions found in `core/storage/router.py`, `core/bootstrap/app_factory.py`, `core/rbac/rate_limit.py` |
| S7 | Refresh-token revocation ("logout everywhere") | — | **Fixed** (Version 2.22.0) — generation-counter-based revocation confirmed present and tested |

**Nothing found in this pass rises to Critical.** The two most consequential open items (S1, S2) are about missing *defense-in-depth* and *automated enforcement*, not about an active, exploitable hole in the application-layer controls that are actually running today — those were checked thoroughly (§8) and hold up.

---

## 10. Performance Issues

| # | Issue | Where | Severity |
|---|---|---|---|
| P1 | 7+ list pages with no pagination UI, silently capped at 25 rows | Frontend — see B4 | High |
| P2 | Dashboard's 11-way parallel fetch is all-or-nothing (one failure blanks the whole page) and several of its inputs are capped at 100 rows with no follow-up fetch, so KPI math can silently under-count | Frontend — see B2, B3 | Medium-High |
| P3 | A handful of master-data list endpoints (catalog brands/collections/warehouses/price-lists, communication channels/templates, sales service-prices, installation crews/notifications) have no client-facing pagination at all | Backend | Low — mitigated by naturally small per-tenant cardinality and, for notifications, a server-side cap |
| P4 | No N+1 query patterns anywhere in the backend | — | **Clean** |
| P5 | Indexes present on all hot filter paths checked, including a dedicated composite-index migration | — | **Clean** |
| P6 | Bundle size unremarkable (119–161 kB first load per route); dashboard's heavy derived computations are properly `useMemo`-wrapped | — | **Clean** |

---

## 11. Recommended Priority List

1. **Extend "Load more" pagination to the remaining list pages** (Orders, Finance Invoices, Finance Expenses, Production, Catalog Brands/Warehouses/Price-Lists) — same pattern already proven on Customers/Leads/Materials in Version 2.19.0. Highest-severity, best-understood, cheapest fix in this report (B4/P1).
2. **Harden the Dashboard fetch**: replace `Promise.all` with `Promise.allSettled` so one failing call degrades gracefully instead of blanking the page, and either raise/paginate the 100-row caps feeding KPI math or clearly label KPIs as "first 100" (B2/B3/P2).
3. **Make the core/module import boundary an actual CI gate**: install `import-linter` (it's already configured, just not present) or wire `pytest tests/test_core_independence.py` into a real CI workflow — right now nothing stops a violating PR from merging except discipline (§5, S2).
4. **Refresh `API_SPECIFICATION.md` and `DATABASE_DESIGN.md`** to cover Orders/Production/Installation/Finance/Reports — 4-5 of 10 shipped modules, ~44 endpoints, are currently undocumented or documented as not-yet-built when they demonstrably are. This is the largest doc-vs-reality gap found (§9 below, S1 cross-ref).
5. **Decide on Purchasing and Marketing sequencing** (or explicitly re-confirm "not yet" as a product decision) — both are named, scoped, and consciously deferred, not accidentally missing; worth a deliberate go/no-go rather than continued silent deferral.
6. **Close the two long-standing deferred items that keep resurfacing**: Customer restore (B6) and Finance/Production list `sort` parameters (B1) — both have been re-identified across multiple audit passes without being picked up.
7. **Add a committed ESLint config** so `npm run lint` actually runs — currently the only enforced static check is `tsc --noEmit`.
8. **Sync `README.md` and `ROADMAP.md`** to Version 2.25.0 (currently stopped at 2.18.0 and 2.23.0 respectively) — low effort, keeps the "living document" claim in `CLAUDE.md` true.
9. Lower-priority hardening: tighten CORS `allow_methods`/`allow_headers`, add a focus trap to the mobile nav drawer, evaluate real Postgres RLS as the promised second tenancy-isolation layer, plan the localStorage→httpOnly-cookie token migration, build the deferred `usePermission()` frontend gating hook.

---

## 12. Estimated Remaining Work

Assuming a pace consistent with this project's own delivery history (most single-module versions in `CHANGELOG.md` shipped in what reads as one focused session each, with full test coverage and live smoke verification):

| Work item | Rough size (per this repo's own S/M/L/XL scale, `ROADMAP.md`) | Estimate |
|---|---|---|
| Pagination rollout to remaining list pages (item 1) | S | 0.5–1 session |
| Dashboard fetch hardening (item 2) | S | 0.5 session |
| CI + import-linter wiring (item 3) | S | 0.5 session (no app code changes, just tooling) |
| API_SPECIFICATION.md / DATABASE_DESIGN.md catch-up (item 4) | M | 1–2 sessions (documentation-only, but 5 modules' worth) |
| Customer restore + Finance/Production sort params (item 6) | S | 0.5–1 session |
| ESLint config + doc sync (items 7–8) | S | 0.5 session |
| **Purchasing module** (new, XL per the roadmap's own sizing of comparable modules like Production/Catalog) | XL | Comparable to Production/Installation's original build — a multi-session module effort |
| **Marketing module** (new, XL) | XL | Comparable scope; explicitly deferred pending Sales/CRM data maturity, which now exists |
| **Mobile client** (Phase 9) | XL, effectively a second frontend | Largest remaining item if pursued; nothing in the current codebase blocks it, but nothing has validated it either |
| RLS defense-in-depth layer, localStorage→cookie migration, frontend permission gating | M each | Each a focused, well-scoped follow-up, not urgent |

**In short**: the polish/bug-fix backlog (items 1–8) is roughly **1–2 weeks of focused work** at this project's demonstrated pace, entirely inside the existing 10 modules. The two genuinely unbuilt modules (Purchasing, Marketing) and the mobile client are each **module-sized efforts** (weeks, not days) and are correctly treated by the project's own roadmap as deliberate future phases rather than overdue work.
