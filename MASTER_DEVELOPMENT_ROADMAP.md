# G-STONE ERP — Master Development Roadmap

_Date: 2026-07-23_
_Current state: Version **2.37.0**. 14 installed modules, 722/722 backend tests passing, CI-enforced core/module architecture boundary (including a CI-enforced ESLint gate — see Phase 17), Postgres Row-Level Security + httpOnly-cookie auth + staff MFA + a compliance audit-log surface (see Phase 18), live in daily use by G-STONE GALLERY._
_Updated 2026-07-23: Phase 18 (Security & Compliance Hardening) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.37.0] and `IMPLEMENTATION_REPORT.md` §10 for the complete record._
_Updated 2026-07-22: Phase 17 (Stabilization & Technical Debt Closeout) delivered in full — moved from Part 3 to Part 2 below. See `CHANGELOG.md` [2.36.0] and `PHASE17_COMPLETION_REPORT.md` for the complete record._
_Built from: the codebase as it stands (`backend/modules/`, `frontend/app/(app)/`), `PROJECT_AUDIT.md` (2026-07-21, commit `521428e`/v2.25.0), `IMPLEMENTATION_REPORT.md` (2026-07-22, v2.25.0→v2.33.0), `STONE_WORKFLOW_REPORT.md` (Phase 1, v2.34.0), the v2.35.0 `CHANGELOG.md` entry (Phase 2), `ROADMAP.md`'s full version history, and `PROJECT_ANALYSIS.md`'s original 11-phase plan._
_Scope: this document does not implement anything. It records what is done (so it isn't re-litigated) and sequences what remains, in execution order, to take the platform from "a real, tested, in-production ERP" to a **world-class Stone Fabrication ERP**._

---

## How to read this document

- **Part 1** defines what "world-class" means for this specific product, so later phases have a target instead of being an arbitrary backlog.
- **Part 2** is the delivery history, compressed from 60+ point releases into 19 coherent phases, each marked ✅ **Completed** with its real version numbers and dates. Nothing here needs to be redone.
- **Part 3** is everything not yet built, sequenced into phases in the order they should be executed, with the reasoning for that order. Phase numbering continues from Part 2 (Phase 19 onward) so the whole platform history reads as one continuous list.
- Every remaining phase cites the source finding it comes from (`PROJECT_AUDIT.md` §, `IMPLEMENTATION_REPORT.md` §, `STONE_WORKFLOW_REPORT.md` §12, or `PROJECT_ANALYSIS.md`'s original Phase 9/10) rather than being invented fresh — this roadmap extends the project's own audit trail, it doesn't restart it.

---

## Part 1 — What "World-Class Stone Fabrication ERP" Means Here

Given what this platform already is (a complete quote-to-cash-to-install ERP with stone-industry-specific slab/reservation/cut-optimization depth no generic ERP has), "world-class" is not "add more modules." It's closing the six gaps between "a complete, correct, well-tested system" and "a system an enterprise stone fabrication business would trust with its whole operation, without caveats":

1. **No open technical debt or known bugs** — every item a prior audit flagged and re-flagged (customer restore, list sorting, dead code, doc drift) is actually closed, not carried forward a fourth time.
2. **Security and compliance with no asterisks** — the defense-in-depth layers the architecture docs already promise (RLS, CI-enforced boundaries, httpOnly tokens, tightened CORS) are real, not "acknowledged as accepted tech debt."
3. **The stone-fabrication domain logic is finished, not just started** — Phase 1/2 of the Stone Fabrication Workflow built the data model and the algorithm; a world-class version closes the UI and operational gaps (reservation UI, drag-and-drop stage boards, notifications, multi-slab optimization, CNC-ready output) those two phases deliberately left for a follow-up.
4. **Every "mock" or "placeholder" abstraction gets a real implementation** — the AI Sales Assistant is explicitly mock-provider-only by design; a real LLM behind the same abstraction is the difference between a demo and a working assistant.
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
Lead scoring, conversation/sales/task intelligence, dedicated AI Dashboard — every recommendation requires explicit human Accept/Reject/Edit. Deliberately `MockAIProvider`-only; the abstraction is real, the model behind it is not yet (see Phase 21).

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

---

## Part 3 — Remaining Phases (Execution Order)

_Sequencing logic: close known debt and security gaps first (cheap, and every later phase inherits a cleaner/safer base) → finish the stone-fabrication domain the last two phases started (the platform's actual competitive differentiator) → extend that domain further (advanced optimization, real supply-chain automation) → replace the one remaining major mock (AI) → close the money/paperwork loop (payments, accounting export) → make analytics scale-ready → prove the system at real scale → extend to mobile → formal hardening and launch, exactly as `PROJECT_ANALYSIS.md`'s own Phase 9/10 always intended to come last._

---

### 🔲 Phase 19 — Stone Fabrication Workflow, Phase 3: Operational Completion
**Priority: High · Size: M · Directly extends Phases 15–16, this platform's core differentiator**

`STONE_WORKFLOW_REPORT.md` §12 named these as deliberate, scoped-out gaps in Phase 1, still open after Phase 2. This phase closes them, turning the reservation/stage/offcut data model into a fully operable daily tool rather than an API-only capability partially surfaced through one page.

- **Reservation UI outside the Production Job page** — today, explicit slab reservation is API-only; there is no "reserve this slab for this order" button anywhere in the UI (Catalog slab list, Order detail). Build it so staff can browse and manage all active reservations directly, not only via quote acceptance.
- **Drag-and-drop stage movement** — Phase 2's Production Planning Dashboard is a real Kanban-by-stage board, but it's a report (read + overdue/workload view), not an interaction surface; moving a job between stages still requires the separate `/production/{id}` panel. Wire drag-and-drop directly on the board.
- **Stage reordering UI** — `sort_order` can only be changed via a direct API call today; expose it on the `/production/stages` settings page (rename/hide already exist there).
- **Priority/stage-change notifications** — an `urgent` job or a stage move to "Quality Control" triggers nothing today; the timeline is pull-only. Wire into the existing in-app notification system Installation already uses.
- **Bulk operations** — reserving multiple slabs, or moving multiple jobs to a new stage together, both require one API call per item today; add bulk endpoints and UI, matching the precedent Customers' bulk actions (Phase 9) already set.
- **Finer-grained production permissions** — every new Phase 1/2 endpoint reuses the same coarse `production:read`/`production:write`; split out at minimum "change priority" from "reassign operator" if role requirements get more specific during Phase 18's RBAC review.
- **Offcut dimension/area validation** — `POST /catalog/slabs/{id}/offcuts` currently accepts any length/width with no plausibility check against the parent slab.
- **`sold` vs. `consumed` reconciliation** — the two terminal slab statuses now overlap in real-world meaning (direct sale vs. fabrication completion) as a convention, not a system-enforced boundary; document or enforce the distinction before it causes a data-quality issue.

---

### 🔲 Phase 20 — Advanced Cut Optimization & Supply Chain Intelligence
**Priority: High · Size: L · Builds on Phase 16's algorithm and Phase 19's completed reservation/stage UI**

Takes the single-slab nesting engine from Version 2.35.0 and turns it into the shop-floor and procurement automation layer a world-class fabrication ERP needs.

- **Multi-slab / cross-job batch optimization** — today's engine optimizes one job against one slab or offcut; extend it to nest multiple queued work orders' pieces across the available slab/offcut inventory at once, minimizing total waste across a whole production run, not just one job at a time.
- **CNC/machine-ready export** — the current output is a visualization SVG; add a DXF (or equivalent CAM-ready) export of a completed cut layout so the optimization result can drive an actual CNC/waterjet machine, not just inform a human operator.
- **Automated low-stock → purchase suggestion** — tie Reports' Inventory Analytics (Phase 10) and the Purchasing module (Phase 12) together: when Smart Offcut Management's `recommend_new_slab` fires repeatedly for a material, or stock for a material drops below a threshold, surface a suggested Purchase Order draft instead of requiring a manager to notice the pattern manually.
- **Standardized supplier catalog import** — Sprint 2 (Phase 9) deliberately kept Brand/Stone/Thickness/Size as free-text-backed curated suggestions rather than real manufacturer spec-sheet data, explicitly deferring this. Build a real import pipeline (CSV/API) for supplier catalogs (NEOLITH, MARAZZI, SAPIENSTONE, etc. — already named as suggested brands) so Materials/Thickness/Size options are sourced from real supplier data instead of typed in by hand.

---

### 🔲 Phase 21 — Real AI Provider Integration
**Priority: Medium-High · Size: L · Sequenced after Phase 18 (security) since real LLM calls carry new data-handling and cost-control obligations**

The AI Sales Assistant (Phase 5) was deliberately built provider-agnostic with every provider name (`openai`/`anthropic`/`gemini`/`ollama`/`azure_openai`) resolving to a deterministic `MockAIProvider` — the abstraction was the point of that phase, not a real model. This phase is the follow-through, mirroring exactly how Phase 7 followed Phase 4 for Communication.

- Implement at least one real `AIProvider` (Claude via the Anthropic API is the natural first choice given this codebase's own tooling) behind the existing interface — no change to any use case, schema, or the frontend, the same non-goal discipline Phase 7 held for channel providers.
- Cost controls and rate limiting on real model calls (this is the first place in the codebase real per-call cost exists).
- Prompt/response audit logging — every AI-generated recommendation should be traceable to the exact prompt and model response that produced it, for the same accountability reason every other write action gets an audit entry.
- Preserve the existing hard invariant: **AI never performs a business action automatically** — every recommendation still requires explicit human Accept/Reject/Edit, enforced structurally, not just by UI convention.
- Natural scope expansion once a real model exists: AI-drafted quote line-item suggestions from a Project's Rooms/Items, AI-drafted customer-message replies in the Communication Center inbox (draft-only, human-sent).

---

### 🔲 Phase 22 — Payments & Financial Ecosystem Integration
**Priority: Medium · Size: L · Sequenced after Phase 18 (security/MFA) since this phase moves real money**

Closes the last gap between "the system tracks financial state" and "the system participates in the financial transaction."

- **Online payment collection on the Customer Portal** — today Customer Portal (Phase 14) is read-only (view invoice balance, can't pay it). Add a real payment gateway integration (e.g., Stripe or a regional equivalent relevant to Azerbaijan) so a customer can pay an invoice directly, closing the "Payment Received" pipeline status's original intent from Phase 0's CRM design.
- **Accounting/ERP export** — G-STONE's own internal navigation already deliberately deprioritizes "1C's territory" (per Phase 9's Sprint 2 sidebar restructuring) without removing that functionality; formalize the other half of that relationship as a real export (or API integration) to whatever accounting system(s) the three companies actually reconcile against, so Finance module data doesn't require manual re-entry elsewhere.
- **E-signature integration** — Measurement sign-off (`customer_signature_document_id`, Phase 9) and Installation's photo/signature capture (Phase 3) both currently rely on manually attaching a signature image/document. A real e-signature provider integration would make this a verifiable, tamper-evident signature rather than an uploaded image.

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
| 0–18 | Foundation through Security & Compliance Hardening | ✅ Completed (v1.0–v2.37.0) | — | — |
| 19 | Stone Fabrication Workflow, Phase 3 | 🔲 Next | M | Phases 15–16 |
| 20 | Advanced Cut Optimization & Supply Chain Intelligence | 🔲 | L | Phase 19 |
| 21 | Real AI Provider Integration | 🔲 | L | Phase 18 ✅ |
| 22 | Payments & Financial Ecosystem Integration | 🔲 | L | Phase 18 ✅ |
| 23 | Reporting & Business Intelligence Maturity | 🔲 | M | None |
| 24 | Performance, Scale & Reliability Engineering | 🔲 | M | Phase 23 (partial) |
| 25 | Mobile Client & Offline Field Operations | 🔲 | XL | Phases 18 ✅, 22 |
| 26 | World-Class Launch Readiness | 🔲 | M | All of the above |
