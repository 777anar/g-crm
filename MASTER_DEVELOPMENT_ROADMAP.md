# G-STONE ERP — Master Development Roadmap

_Date: 2026-07-24_
_Current state: Version **2.43.0**. 14 installed modules, 831/831 backend tests passing, CI-enforced core/module architecture boundary (including a CI-enforced ESLint gate — see Phase 17), Postgres Row-Level Security + httpOnly-cookie auth + staff MFA + a compliance audit-log surface (see Phase 18), a fully operable reservation/stage/notification UI closing every Phase 1/2 Stone Fabrication Workflow gap (see Phase 19), multi-slab batch optimization + CNC/DXF export + automated low-stock purchase suggestions + a real supplier catalog import pipeline (see Phase 20), a real Anthropic Claude provider behind the AI Sales Assistant with cost controls, a full prompt/response audit trail, and AI draft generation for Quote line items and Communication replies (see Phase 21), real Stripe-backed online payment collection on the Customer Portal, a CSV/journal accounting export, and a real Dropbox Sign e-signature integration for measurement and installation sign-off (see Phase 22), live in daily use by G-STONE GALLERY._
_Updated 2026-07-24: Phase 22 (Payments & Financial Ecosystem Integration) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.43.0] and `IMPLEMENTATION_REPORT.md` §15 for the complete record._
_Updated 2026-07-24: Phase 21's own follow-through — AI draft generation for Quote line items and Communication Center replies — delivered in full. See `CHANGELOG.md` [2.42.0] and `IMPLEMENTATION_REPORT.md` §14 for the complete record._
_Updated 2026-07-24: Phase 21 (Real AI Provider Integration) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.40.0] and `IMPLEMENTATION_REPORT.md` §13 for the complete record._
_Updated 2026-07-24: Phase 20 (Advanced Cut Optimization & Supply Chain Intelligence) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.39.0] and `IMPLEMENTATION_REPORT.md` §12 for the complete record._
_Updated 2026-07-23: Phase 19 (Stone Fabrication Workflow, Phase 3) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.38.0] and `IMPLEMENTATION_REPORT.md` §11 for the complete record._
_Updated 2026-07-23: Phase 18 (Security & Compliance Hardening) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.37.0] and `IMPLEMENTATION_REPORT.md` §10 for the complete record._
_Updated 2026-07-22: Phase 17 (Stabilization & Technical Debt Closeout) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.36.0] and `PHASE17_COMPLETION_REPORT.md` for the complete record._
_Built from: the codebase as it stands (`backend/modules/`, `frontend/app/(app)/`), `PROJECT_AUDIT.md` (2026-07-21, commit `521428e`/v2.25.0), `IMPLEMENTATION_REPORT.md` (2026-07-22, v2.25.0→v2.33.0), `STONE_WORKFLOW_REPORT.md` (Phase 1, v2.34.0), the v2.35.0 `CHANGELOG.md` entry (Phase 2), `ROADMAP.md`'s full version history, and `PROJECT_ANALYSIS.md`'s original 11-phase plan._
_Scope: this document does not implement anything. It records what is done (so it isn't re-litigated) and sequences what remains, in execution order, to take the platform from "a real, tested, in-production ERP" to a **world-class Stone Fabrication ERP**._

---

## How to read this document

- **Part 1** defines what "world-class" means for this specific product, so later phases have a target instead of being an arbitrary backlog.
- **Part 2** is the delivery history, compressed from 60+ point releases into 20 coherent phases, each marked ✅ **Completed** with its real version numbers and dates. Nothing here needs to be redone.
- **Part 3** is everything not yet built, sequenced into phases in the order they should be executed, with the reasoning for that order. Phase numbering continues from Part 2 (Phase 22 onward) so the whole platform history reads as one continuous list.
- Every remaining phase cites the source finding it comes from (`PROJECT_AUDIT.md` §, `IMPLEMENTATION_REPORT.md` §, `STONE_WORKFLOW_REPORT.md` §12, or `PROJECT_ANALYSIS.md`'s original Phase 9/10) rather than being invented fresh — this roadmap extends the project's own audit trail, it doesn't restart it.

---

## Part 1 — What "World-Class Stone Fabrication ERP" Means Here

Given what this platform already is (a complete quote-to-cash-to-install ERP with stone-industry-specific slab/reservation/cut-optimization depth no generic ERP has), "world-class" is not "add more modules." It's closing the six gaps between "a complete, correct, well-tested system" and "a system an enterprise stone fabrication business would trust with its whole operation, without caveats":

1. **No open technical debt or known bugs** — every item a prior audit flagged and re-flagged (customer restore, list sorting, dead code, doc drift) is actually closed, not carried forward a fourth time.
2. **Security and compliance with no asterisks** — the defense-in-depth layers the architecture docs already promise (RLS, CI-enforced boundaries, httpOnly tokens, tightened CORS) are real, not "acknowledged as accepted tech debt."
3. **The stone-fabrication domain logic is finished, not just started** — Phase 1/2 of the Stone Fabrication Workflow built the data model and the algorithm; a world-class version closes the UI and operational gaps (reservation UI, drag-and-drop stage boards, notifications, multi-slab optimization, CNC-ready output) those two phases deliberately left for a follow-up.
4. **Every "mock" or "placeholder" abstraction gets a real implementation** — the AI Sales Assistant was explicitly mock-provider-only by design until Phase 21 gave it a real Claude-backed provider behind the same abstraction, the difference between a demo and a working assistant.
5. **The business runs on it end-to-end, including money and hardware** — no online payment collection, no accounting-system export, no CNC/machine-file export exists yet. These are the remaining links between "the system has the data" and "the data leaves the system to do something."
6. **It's validated at the scale and on the devices real usage requires** — mobile client (explicitly Phase 9 of the original architecture, never started) and load/performance testing (explicitly Phase 10, never started) are the two phases the original plan always intended to come last, and still haven't happened.

Parts 2 and 3 below are organized around closing these six gaps, in the order that minimizes rework and respects real dependencies (e.g., security hardening before payments touch the system; the reservation UI before multi-slab optimization builds further on top of it).

---

## Part 2 — Completed Phases ✅

_Every phase below shipped, was verified (backend test suite + `tsc --noEmit` + production build + a live smoke test against the running app, per this project's own established practice), and is in current use. Version numbers are exact; dates are from `CHANGELOG.md`/`ROADMAP.md`._

### ✅ Phase 0 — Foundation: Core Platform & CRM
**v1.0 · 2026-06-30**
Multi-company, trilingual core platform (auth, RBAC, audit log, event bus, module registry, storage) plus the first module: a stone-industry CRM (Customer/Lead/pipeline, 9 lead channels, dashboard, search/sort/keyboard shortcuts).

### ✅ Phase 1 — Stone Catalog Module
**v2.0 · 2026-06-30**
Brands, collections, stone materials, slabs (with lifecycle), warehouses, price lists — the system of record every downstream module quotes, orders, and fabricates against.

### ✅ Phase 2 — Sales & Orders
**v2.1–2.2 · 2026-07-01**
Quotes (sections, measurements, items, PDF export) built from real Catalog data; Orders created from an accepted Quote, driving the `OrderApproved` event.

### ✅ Phase 3 — The Rest of the Original Module Chain
**v1.2, v2.3–2.6 · 2026-07-04 – 2026-07-06**
Tasks & Reminders, Reports (executive dashboard + cross-module analytics + PDF/Excel export), Production (work orders consuming slabs), Installation (scheduling, crews, photo/signature capture), Finance (invoicing, payments, expenses). This completes the CRM → Catalog → Sales → Orders → Production → Installation → Finance → Reports chain from `PROJECT_ANALYSIS.md` §2 — 8 of the original 10 modules.

### ✅ Phase 4 — Communication Center
**v2.7 · 2026-07-06**
Unified omnichannel inbox (WhatsApp, Instagram, Messenger, Email, SMS) integrated with CRM, behind a `ChannelProvider` abstraction (initially `NullChannelProvider`-only, by design).

### ✅ Phase 5 — AI Sales Assistant (mock provider)
**v2.8 · 2026-07-06**
Lead scoring, conversation/sales/task intelligence, dedicated AI Dashboard — every recommendation requires explicit human Accept/Reject/Edit. Deliberately `MockAIProvider`-only at the time; a real Claude-backed provider was added behind the same abstraction in Phase 21.

### ✅ Phase 6 — UX & Platform Polish
**v2.8.1 · 2026-07-06**
Design-system foundation (tokens, dark mode), table toolkit (resize/visibility/saved filters/sticky headers), form UX (`loading` states, `Toast`), mobile slide-over nav, accessibility baseline (`:focus-visible`, skip-link, ARIA), print/PDF layout, dashboard `useMemo` pass.

### ✅ Phase 7 — Real Channel Integrations
**v2.9 · 2026-07-06**
Real WhatsApp Business Cloud / Instagram Messaging / Messenger Send (Meta Graph API), SMTP+IMAP, Twilio SMS, and a generic webhook provider replace `NullChannelProvider`; encrypted per-company credential store, signature-verified inbound webhooks, delivery-status reconciliation, retry queue, diagnostics/logs admin surface.

### ✅ Phase 8 — Enterprise Polish & Production Readiness
**v2.9.1–2.9.3 · 2026-07-07 – 2026-07-08**
Three successive audit-and-fix passes: logging, N+1 query fix, silent-failure fixes on write actions, boot-time secret-default guards, request-id-correlated error logging, then a full application-perspective CRUD/navigation/i18n/responsive audit (favicon, breadcrumbs on 10 detail pages, Quote Settings UI, Brands/Warehouses archive UI, chart dark-mode fixes).

### ✅ Phase 9 — G-STONE Daily-Operations Deepening
**v2.10–2.23 · 2026-07-xx** (Sprints 2–8 + the remaining Version 1.1/1.2 backlog)
Navigation restructured around "Layihə" (Project); Rooms → Project Items → Materials/Measurements/Drawings/Photos data model; production-ready Brand→Stone→Thickness→Size material selector; the complete 10-tab project workflow including per-piece "Təhvil" (handover) tracking; operational Dashboard redesign; CSV export; Assigned Manager picker; a 6-research-pass full-app UX audit; "Load more" pagination + shareable filters + bulk actions on Customers/Leads; refresh-token revocation (logout-everywhere); Customer Type picker. This phase closed every remaining item from the original Version 1.1/1.2 plans.

### ✅ Phase 10 — Executive Dashboard & Information-Architecture Consolidation
**v2.24–2.25 · 2026-07-xx**
Dashboard rewired onto real server-side executive aggregation (revenue/profit/KPIs/trend); primary sidebar consolidated from 9 sections to 6 (Dashboard/Sales/Orders-Projects merged/Inventory/Finance/Reports/Settings); Inventory Analytics endpoint and Reports tab.

### ✅ Phase 11 — Post-Audit Remediation Round 1
**v2.26–2.30 · 2026-07-21 – 2026-07-22**
Directly closes `PROJECT_AUDIT.md` priorities #1–4: "Load more" pagination extended to Orders/Production/Finance Invoices/Finance Expenses/Catalog Brands; Dashboard fan-out hardened (`Promise.allSettled`, cursor-following stat fetches); `import-linter` actually wired up plus a real `.github/workflows/ci.yml`; `API_SPECIFICATION.md`/`DATABASE_DESIGN.md` fully rewritten against real code; a real cursor-pagination bug (`next_cursor` hardcoded `null`) found and fixed across 5 endpoints.

### ✅ Phase 12 — Purchasing Module
**v2.31 · 2026-07-22**
Suppliers, Purchase Orders (full status lifecycle), receiving that creates real `catalog_slabs` rows via Catalog's own use case — closes the restocking loop. 9th of the original 10 modules.

### ✅ Phase 13 — Marketing Module
**v2.32 · 2026-07-22**
Campaigns, lead attribution (`crm_leads.campaign_id`), live conversion/revenue performance computed from real Order data. **Completes the original 10-module plan from `PROJECT_ANALYSIS.md` §2 in full.**

### ✅ Phase 14 — Customer Portal
**v2.33 · 2026-07-22**
First module beyond the original 10-module scope: a fully separate customer authentication identity, staff-side access management, and a self-service read surface (orders/quotes/invoices/installation/documents) with financial fields (internal cost/profit/margin) structurally excluded from every customer-facing schema.

### ✅ Phase 15 — Stone Fabrication Workflow, Phase 1
**v2.34 · 2026-07-22**
Material Reservation (`catalog_slab_reservations`, double-booking guard, explicit + quote-adopted reservation), extended slab lifecycle (`received`→`available`→`reserved`→`in_production`→`offcut_created`/`consumed`/`scrap`, 5→8 states), configurable per-company Production Stages, Work Order priority/operator assignment/stage tracking, and a human-readable Timeline (`work_order_events`) layered on top of the mandatory audit log.

### ✅ Phase 16 — Stone Fabrication Workflow, Phase 2
**v2.35 · 2026-07-22**
Cut Optimization engine (pure shelf/guillotine nesting algorithm, kerf-aware, rotation-aware, real-mm SVG visualization), Smart Offcut Management (ranks existing offcuts by utilization before ever suggesting a new slab), Offcut Library (filtered slab search), Optimization History (immutable, reopenable snapshots), and a Production Planning Dashboard (Kanban-by-stage board with overdue highlighting and per-operator workload).

### ✅ Phase 17 — Stabilization & Technical Debt Closeout
**v2.36 · 2026-07-22**
Eight findings independently re-identified across two or more prior audit passes without being picked up, closed in one pass: customer archive restore (B6), Finance invoice/Production work-order list `sort` parameters (B1), a committed and CI-enforced ESLint configuration (surfacing and genuinely fixing 93 pre-existing violations, not suppressing them), `module_permissions` wired into a real `hasPermission()`/`usePermission()` frontend utility instead of staying dead data (B7), the `crm_customers`↔`crm_contacts` circular FK warning resolved via `use_alter` (B5, no migration needed), a tablet-width (768–1023px) icon-only collapsed sidebar, a keyboard focus trap on the mobile nav drawer, and Lucide adopted as the single icon library replacing 9 hand-rolled inline SVGs across 6 components. Full detail in `PHASE17_COMPLETION_REPORT.md`.

### ✅ Phase 18 — Security & Compliance Hardening
**v2.37 · 2026-07-23**
Closed every gap Part 1's pillar #2 named: Postgres Row-Level Security (RLS enabled + a `company_isolation` policy on all 75 tenant-owned tables, wired automatically per-request via a new `CompanyContextMiddleware` + a SQLAlchemy `after_begin` hook — zero router/repository changes needed, no-ops on SQLite); staff and Customer Portal auth tokens moved from `localStorage` to httpOnly/`Secure`/`SameSite=Lax` cookies (both auth flows now accept either the cookie or a Bearer header, so existing API clients/tests were unaffected while the browser frontend now never touches a raw token); CORS `allow_methods`/`allow_headers` no longer wildcarded; and the `usePermission()` frontend-gating utility Phase 17 introduced on the Customers pages only rolled out to all 32 remaining files with a write action across every module. Two items beyond that pillar's original list, both explicitly named in this phase's own scope: staff TOTP MFA (self-service enroll/enable/disable, a login-time challenge/response step, and a per-company-per-role mandatory-MFA policy — the "optional-then-mandatory-per-role" control), and a compliance audit-log export/retention admin surface (filterable CSV export, a configurable retention window, and a manual, owner-triggered purge — deliberately manual since no background job queue exists yet). 16 new backend tests (706→722). Full detail in `CHANGELOG.md` [2.37.0] and `IMPLEMENTATION_REPORT.md` §10.

### ✅ Phase 19 — Stone Fabrication Workflow, Phase 3: Operational Completion
**v2.38 · 2026-07-23**
Closed every one of the eight gaps `STONE_WORKFLOW_REPORT.md` §12 named as the deliberately-scoped Phase 1/2 boundary: a reservation UI outside the Production Job page (bulk-select-and-reserve on `/catalog/slabs`, a new company-wide `/catalog/reservations` browse-and-release page, and a Reserved Slabs card on `/orders/{id}`); real drag-and-drop stage movement plus a multi-select bulk-move toolbar on the Production Planning Dashboard; move-up/move-down stage reordering on `/production/stages`; a new Production notification subsystem (mirroring Installation's `notify_crew` pattern) firing on urgent-priority, stage-change, and operator-assignment moments, surfaced on the Dashboard; bulk slab reservation and bulk stage movement (both frontend `Promise.allSettled` fan-outs, matching the only bulk-action convention this codebase actually has); `production:priority:write`/`production:operator:write`/`production:stage:write` splitting the previously-coarse `production:write`; offcut dimension/area plausibility validation (checked in both orientations against the parent slab); and the `sold`-vs-`consumed` boundary closed two ways (`consumed` now reachable only via Production's own completion cascade; selling/scrapping a still-reserved slab now auto-releases its dangling reservation instead of leaving it stuck `active`). 15 new backend tests (722→737). Full detail in `CHANGELOG.md` [2.38.0] and `IMPLEMENTATION_REPORT.md` §11.

### ✅ Phase 20 — Advanced Cut Optimization & Supply Chain Intelligence
**v2.39 · 2026-07-24**
Took the single-slab nesting engine from Version 2.35.0 and turned it into the shop-floor and procurement automation layer named as this phase's goal: multi-slab/cross-job batch optimization (`POST /cut_optimization/batch-runs`, a new `pack_pieces_multi_slab` outer orchestrator reusing the existing single-slab packer unchanged, persisted to a new `cut_optimization_batch_runs` table, with a job-identifier label-prefix convention for tracking which job a placement belongs to); CNC/machine-ready export (`GET .../export.dxf` on both single-slab and batch runs, `ezdxf`-based, `SLAB`/`CUT`/`LABELS` layers); automated low-stock → purchase suggestion (`GET /reports/inventory/low-stock`, combining a configurable available-stock threshold with Smart Offcut Management's own `no_suitable_offcut` audit-log history, surfaced on `/reports/inventory` linking into Purchasing's existing PO-creation form rather than adding a new write path); and a standardized supplier catalog import pipeline (`POST /catalog/materials/import`, CSV find-or-create/upsert for Brands/Materials/Thicknesses/Sizes, best-effort per row) closing Sprint 2 (Phase 9)'s deliberately-deferred free-text-only catalog data entry. 21 new backend tests (737→758). Full detail in `CHANGELOG.md` [2.39.0] and `IMPLEMENTATION_REPORT.md` §12.

### ✅ Phase 21 — Real AI Provider Integration
**v2.40 · 2026-07-24**
Gave the AI Sales Assistant (Phase 5, Version 2.8) its first real model behind the existing `AIProvider` interface: `anthropic` now resolves to a real `AnthropicProvider` calling the Claude API with structured JSON output, asked only for the genuinely language/judgment half of each analysis (score, sentiment, phrasing, ranking within an already-real candidate list) — exact-id matching and financial-threshold math are computed deterministically (new `modules/ai/domain/analysis_helpers.py`) and merged in, so a hallucinated id or an approximated figure is structurally impossible, not just unlikely. No use case, DTO, schema, or frontend change was needed for the swap itself, the same non-goal discipline Phase 7 held for Communication's channel providers. Cost controls closed the phase's other named requirement: every analysis call (mock or real) is rate-limited per company and checked against a configurable daily spend cap before the provider is invoked, both enforced from a new `ai_provider_call_logs` audit table that records every call attempt — success, rejection, or failure — with its exact prompt, raw response, tokens, cost, and latency; `AIRecommendation` gained a `provider_call_id` tracing every recommendation back to the call that produced it, and a new `GET /ai/usage` endpoint (surfaced on the AI Dashboard) makes today's spend/budget/call history visible rather than only enforced. The existing "AI never performs a business action automatically" invariant required no new code to preserve, since `ReviewRecommendationUseCase` was already recommendation-type-agnostic. 16 new backend tests (758→774). Full detail in `CHANGELOG.md` [2.40.0] and `IMPLEMENTATION_REPORT.md` §13.

**Follow-through — v2.42 · 2026-07-24**: the two "deliberately out of scope" product surfaces named above — AI-drafted Quote line items and AI-drafted Communication Center replies — are now built behind the same `AIProvider` interface, closing this phase for good. `draft_conversation_reply`/`draft_quote_line_items` were added to the `AIProvider` abstract base (implemented in both `MockAIProvider` and `AnthropicProvider`); two new recommendation types (`suggested_reply`, `quote_draft_line_items`) reuse the existing `ANALYSIS_KIND_CONVERSATION`/`ANALYSIS_KIND_QUOTE` categories and the existing `ai_recommendations` table (no new migration). The same deterministic-boundary discipline applies: the model only supplies reply text / a line-item description / a bounded 0–20% waste factor, while exact `project_item_id`s, quantities, and prices are always computed or validated in code — a hallucinated id is filtered out and an out-of-range waste factor is clamped, both defensively and under test. Both features are strictly draft-only: `POST /ai/conversations/{id}/draft-reply` creates a `suggested_reply` recommendation the Communication inbox lets a rep load into the compose box (same convenience as picking a template — nothing is sent automatically); `POST /ai/projects/{id}/draft-quote-items` creates a `quote_draft_line_items` recommendation the Sales Project page renders as a review table (nothing is written to a Quote automatically). 13 new backend tests (780→793). Full detail in `CHANGELOG.md` [2.42.0].

### ✅ Phase 22 — Payments & Financial Ecosystem Integration
**v2.43 · 2026-07-24**
Closed the last gap between "the system tracks financial state" and "the system participates in the financial transaction," all three items named. **Online payment collection**: a new `PaymentGatewayProvider` abstraction (`modules/finance/infrastructure/providers/`, mock-by-default plus a real `StripeProvider` using the official `stripe` SDK's Checkout Sessions) backs the Customer Portal's first-ever write action — `POST /customer_portal/me/invoices/{id}/pay` starts a hosted checkout for an invoice's full outstanding balance, tracked in a new `invoice_payment_sessions` table, resolved to a real `Payment` only once a gateway webhook confirms the charge (never trusted from the browser's own success-redirect) by reusing `RecordPaymentUseCase` completely unchanged. A mock-only "simulate" endpoint makes the whole flow demoable with no real Stripe account. **Accounting/ERP export**: `GET /finance/export/{invoices|payments|expenses|journal}` (CSV, matching Purchasing's existing export convention) — the `journal` resource is a synthesized double-entry-style export (debit/credit rows for every Invoice/Payment/Expense) any accounting system (1C and similar are the norm for these three companies) can import as journal entries, not just a raw table dump. **E-signature integration**: a new `core/esignature/` provider library (mock-by-default plus a real `DropboxSignProvider` using the official `dropbox_sign` SDK) — cross-cutting infrastructure shared by two modules, so it lives in core exactly like `core/storage`'s Document client, never importing either module. Sales' measurement sign-off and Installation's job-completion sign-off each gained their own `request-signature`/`simulate-signature`/public webhook endpoints and three tracking columns (`signature_status`/`signature_provider`/`signature_provider_request_id`); completion still lands in the exact same place the manual path already used — `customer_signature_document_id` for a measurement, a `photo_type="signature"` `InstallationPhoto` for a job — so both manual-upload and e-signature paths coexist. Every webhook-originated write (payment or signature) is attributed to the underlying record's own `created_by`, mirroring Communication's identical channel-webhook attribution guard, since no authenticated staff user exists for an external callback. 38 new backend tests (793→831). Full detail in `CHANGELOG.md` [2.43.0] and `IMPLEMENTATION_REPORT.md` §15.

---

## Part 3 — Remaining Phases (Execution Order)

_Sequencing logic: close known debt and security gaps first (cheap, and every later phase inherits a cleaner/safer base) → finish the stone-fabrication domain the last two phases started (the platform's actual competitive differentiator) → extend that domain further (advanced optimization, real supply-chain automation) → replace the one remaining major mock (AI) → close the money/paperwork loop (payments, accounting export) → make analytics scale-ready → prove the system at real scale → extend to mobile → formal hardening and launch, exactly as `PROJECT_ANALYSIS.md`'s own Phase 9/10 always intended to come last._

---

### 🔲 Phase 23 — Reporting & Business Intelligence Maturity
**Priority: Medium · Size: M**

- **SQL-side aggregation** — Reports' cross-module analytics currently do `sum()`/grouping in Python over fetched ORM rows rather than SQL-side `SUM`/`GROUP BY` — flagged in `PROJECT_AUDIT.md`'s Enterprise Polish audit (Phase 8) as a real future scaling concern, deliberately deferred rather than rushed under a "no business logic changes" mandate at the time. Revisit now, carefully, with analytics-correctness regression tests as the explicit acceptance bar.
- **Custom/scheduled report builder** — today's Reports module is a fixed set of dashboards (Sales/Production/Installation/Finance/Inventory/Executive/Production Planning) with PDF/Excel export on demand. Add ad hoc report definitions and scheduled email delivery for recurring stakeholder reports (e.g., a weekly executive summary).
- **BI/data-warehouse export** — a structured export surface (API or scheduled file drop) for external BI tools (Power BI, Metabase, etc.), so cross-company/historical analysis isn't limited to what the in-app Reports module was specifically built to show.

---

### 🔲 Phase 24 — Performance, Scale & Reliability Engineering
**Priority: Medium · Size: M · This is `PROJECT_ANALYSIS.md`'s original Phase 10 ("Hardening & launch") load/perf half, executed once there's real production data volume to test against**

- **Load/performance testing** against realistic multi-company, high-record-volume data — never done; `PROJECT_ANALYSIS.md` §11 named this explicitly as part of the original Phase 10 plan.
- **Redis caching expansion** — Redis is currently used only for refresh-token revocation (Phase 9) and rate limiting; evaluate real caching for hot, expensive queries (Reports aggregations especially, once Phase 23's SQL-side rework lands) rather than recomputing on every request.
- **Background job queue** — PDF generation (Quotes, Invoices, Reports), Cut Optimization runs at scale, and any future bulk import (Phase 20's supplier catalog import) are all currently synchronous request-response work. A real job queue (Celery, already anticipated in `PROJECT_ANALYSIS.md`'s risk table for event-handler throughput) removes the ceiling on how large these operations can get before they start timing out requests.
- **Production Postgres deployment validation** — migrations, backups, monitoring, and a genuine backup/restore drill against Postgres/Supabase (the documented production target; today's dev/test environment runs entirely on in-memory SQLite by design). `PROJECT_ANALYSIS.md` §11 names a backup/restore drill explicitly as part of the original Phase 10 plan; it has never been executed.

---

### 🔲 Phase 25 — Mobile Client & Offline Field Operations
**Priority: Medium · Size: XL · This is `PROJECT_ANALYSIS.md`'s original Phase 9, unstarted since the architecture doc was written — "the first real test of API/mobile parity claims"**

- The core platform has been built API-first/mobile-ready by design since Phase 0 (`PROJECT_ANALYSIS.md` §4.7), but that promise has never been exercised by an actual client. This phase is where it gets proven, not assumed.
- **Field crew / installer app** — job details, photo/signature capture, and status updates for Installation crews, with offline capability for job sites without reliable connectivity (installation work is inherently on-site, unlike every other role this platform serves today).
- **Sales rep mobile access** — CRM/Quote access on the go, matching the original architecture's mobile-parity intent for the highest-mobility role in the business.
- **Customer Portal mobile optimization** — either a responsive PWA pass or a native wrapper around the existing Customer Portal (Phase 14), so customers checking an order/invoice/installation date aren't required to use a desktop browser.
- Sequenced after Phase 18 (security/MFA) and Phase 22 (payments) specifically because a mobile client widens the attack surface and, if it carries payment or signature capabilities, needs those foundations already in place.

---

### 🔲 Phase 26 — World-Class Launch Readiness
**Priority: Ongoing/Final · Size: M · This is `PROJECT_ANALYSIS.md`'s original Phase 10 security-review half, plus Phase 11's "iteration" principle validated**

The closing phase, not because there's nothing left after it, but because it's where the whole platform gets certified against the six pillars from Part 1 at once, the same way Phase 8's "Enterprise Polish" pass certified the state of the platform at that point in time.

- **Full security review** — a from-scratch pass (import-boundary checks, event-scoping checks, the specific items named in `PROJECT_ANALYSIS.md` §11's original Phase 10 scope) once Phases 18/21/22 have all landed and there's new surface area to re-audit.
- **Staged rollout validation per company** — G-STONE GALLERY is the current real-usage baseline; confirm KORONA PREMIUM and NEOLITH BAKU are genuinely ready for the same daily-use load, not just schema-compatible.
- **A fresh, full-codebase audit** in the exact style of `PROJECT_AUDIT.md` — re-run the same method (independent backend/frontend deep-dive passes, doc-vs-code drift check, full test suite + `lint-imports` + `tsc` + build) against the state of the platform after Phases 17–25, to confirm the "no open technical debt" pillar from Part 1 is genuinely true, not just believed to be.
- **Documentation currency pass** — bring `PROJECT_ANALYSIS.md`, `DATABASE_DESIGN.md`, `API_SPECIFICATION.md`, `UI_UX_GUIDELINES.md`, and `ROADMAP.md` current one final time, matching the discipline Phase 11 already established, so the frozen design docs remain the accurate source of truth `CLAUDE.md` says they are.
- **Validate Phase 11 of `PROJECT_ANALYSIS.md`'s original plan** — confirm that adding one more module today still requires zero changes to the modules that already exist (the manifest/event contract's actual test), the same structural claim Phase 8's AI module build already proved once.

---

## Summary Table

| # | Phase | Status | Size | Depends on |
|---|---|---|---|---|
| 0–21 | Foundation through Real AI Provider Integration | ✅ Completed (v1.0–v2.40.0) | — | — |
| 22 | Payments & Financial Ecosystem Integration | 🔲 Next | L | Phase 18 ✅ |
| 23 | Reporting & Business Intelligence Maturity | 🔲 | M | None |
| 24 | Performance, Scale & Reliability Engineering | 🔲 | M | Phase 23 (partial) |
| 25 | Mobile Client & Offline Field Operations | 🔲 | XL | Phases 18 ✅, 22 |
| 26 | World-Class Launch Readiness | 🔲 | M | All of the above |
