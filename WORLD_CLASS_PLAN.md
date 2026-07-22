# G-STONE ERP — World-Class Plan

**Prepared by:** Independent technical/product review
**Baseline:** commit `8fc6506`, Version 2.35.0, 2026-07-22
**Sources reviewed:** `ROADMAP.md` (707 lines, full version history 1.0 → 2.35.0), `CHANGELOG.md`, `PROJECT_ANALYSIS.md` (frozen architecture), `DATABASE_DESIGN.md`, `API_SPECIFICATION.md`, `PROJECT_AUDIT.md`, `RELEASE_CHECKLIST.md`, `MASTER_AUDIT_REPORT.md` (this reviewer's own prior business-logic audit), and direct inspection of `backend/` (755 Python files, 14 installed modules) and `frontend/` (69 routes).
**Constraints honored:** no code was written or modified; no existing file was changed; this document is the only file created.

---

## 1. How to Read This Document

`ROADMAP.md` is not a forward-looking wishlist that the team is behind on — it is closer to a **build log with a plan bolted onto the front of it**. Reading all 36 version entries end to end shows a project that has, with only a handful of exceptions, executed its own plan faithfully: every module named in the original 10-module list (`PROJECT_ANALYSIS.md` §2) is built, plus four more beyond it. The gaps that remain are not "the team hasn't gotten to it yet" in the generic sense — several are **named explicitly in the roadmap's own text, multiple times, across multiple sessions**, as consciously deferred decisions. This document treats those differently from silent omissions, because they carry different risk: a consciously-deferred item usually has a clear reason recorded for *why* it was skipped, which matters when deciding whether to finally build it.

This document answers ten specific questions, in order, and closes with a sequenced execution plan.

---

## 2. Roadmap Compliance Matrix — What's Actually Done vs. Planned

### 2.1 Core Platform & Original 10-Module Plan (`PROJECT_ANALYSIS.md` §2, `ROADMAP.md` Version 2.0)

| Item | Status | Evidence |
|---|---|---|
| Core platform (auth, RBAC, audit, event bus, storage, module registry) | ✅ **Complete** | Frozen since Phase 1; unchanged in shape since |
| CRM (Customers, Leads, Pipeline) | ✅ **Complete** | Version 1.0, hardened through 1.1/2.17–2.23 |
| Tasks & Reminders | ✅ **Complete** | Version 1.2, 2026-07-06 |
| Stone Catalog (Inventory) | ✅ **Complete** | Version 2.0, 2026-06-30; deepened repeatedly since (2.12, 2.34, 2.35) |
| Sales (Quotes/Projects) | ✅ **Complete** | Version 2.0 → massively deepened through 2.11–2.13 into the 10-tab Project workspace |
| Orders | ✅ **Complete** | Version 2.0, 2026-07-01 |
| Production | ✅ **Complete** | Version 2.0 → deepened in 2.34.0 (stages, priority, operator, timeline) |
| Installation | ✅ **Complete** | Version 2.0, 2026-07-04 |
| Finance | ✅ **Complete, but narrow** — see §3 | Version 2.0, 2026-07-06; invoicing/payments/expenses only, no GL (see `MASTER_AUDIT_REPORT.md` §4.1) |
| Reports | ✅ **Complete** | Version 2.0 → real cross-module data restored for every analytics stream by 2.25.0 (previously several were "proxy over Orders" until their real modules existed) |
| Purchasing | ✅ **Complete** | Version 2.31.0, 2026-07-21 — the *last* of the original two unbuilt modules |
| Marketing | ✅ **Complete** | Version 2.32.0, 2026-07-21 — closes the original ten-module plan entirely |

**All ten originally-planned modules are done.** The plan itself records this milestone explicitly: "Purchasing and Marketing... both shipped as of Version 2.32.0."

### 2.2 Beyond the Original Plan

| Item | Status | Evidence |
|---|---|---|
| Communication Center | ✅ Complete (Version 2.7) + real provider integrations (Version 2.9) | WhatsApp/Instagram/Messenger/SMTP/Twilio/webhook all real, signature-verified |
| AI Sales Assistant | 🟡 **Complete, deliberately limited** | Structurally complete (27 recommendation types, human-approval-only by design), but every provider resolves to `MockAIProvider` — no real LLM ever called. This is explicit, documented scope, not a bug |
| Customer Portal | ✅ Complete (Version 2.33.0) | Separate auth identity, whitelisted read surface |
| Stone Fabrication Workflow Phase 1 (Reservation/Lifecycle/Stages) | ✅ Complete (Version 2.34.0) | |
| Stone Fabrication Workflow Phase 2 (Cut Optimization/Offcuts) | ✅ Complete (Version 2.35.0) | |
| Mobile client (Phase 9 of `PROJECT_ANALYSIS.md`) | ❌ **Not started** | No mobile codebase exists anywhere in the repo; architecture is API-first by design but this promise is unvalidated by an actual client |

### 2.3 Version 1.1 — "Finish What 1.0 Started"

Every item is closed. The roadmap's own text confirms this explicitly at Version 2.22.0: *"This closes out every genuinely actionable item from Version 1.1."* The one line item that looked open for a long time (`customer.type`/`Contact` reconciliation) was a **deliberate, recorded product decision pending a choice**, not neglect — the choice (build a picker) was made and delivered in Version 2.23.0. `GetCustomerProfileUseCase`'s `contacts` field (M8) remains intentionally untouched because removing it would be a breaking API change with no corresponding product need.

### 2.4 Version 1.2 — "Make the CRM the Place Reps Actually Live"

This is where genuine, still-open gaps live — and the roadmap says so itself, verbatim, at Version 2.16.0: *"Version 1.2's non-Tasks items (configurable pipeline stages, role-scoped views, CSV export) remain the only items never picked up."* CSV export has since shipped (2.16.0). The rest have not:

| Item | Status | Notes |
|---|---|---|
| Tasks & Reminders | ✅ Delivered 2026-07-06 | |
| CSV Export | ✅ Delivered 2026-07-10 (2.16.0) | |
| **Per-company configurable pipeline stages & lead sources** | ❌ **Still missing** | The 14 CRM pipeline statuses and 9 lead channels remain platform-wide hardcoded, four versions after Production got exactly this capability (configurable `production_stages`, Version 2.34.0). This is now an inconsistency between two parts of the same product, not just an unbuilt feature |
| **Role-scoped Dashboard/list views** ("my customers" vs "all customers") | ❌ **Still missing** | No `assigned_to_me` filter or role-conditional default view exists on any list page |
| **Email/SMS delivery for Task reminders** | ❌ **Still missing** | Reminders remain in-app-only, generated by a pull endpoint the frontend calls on page load — there is still no background job scheduler anywhere in the codebase (Celery/Redis remain provisioned but unused for this purpose) |
| **Attachment previews/thumbnails** | ❌ **Still missing** | Named as open in Version 2.18.0's own "deliberately deferred" list; images in Attachments cards still render as filenames only |
| **Mobile-responsive verification pass** | ✅ Effectively delivered | Superseded by Version 2.8.1's full mobile-nav rebuild and reconfirmed working since |

### 2.5 The "Executive Redesign" (Milestone 1–2, Versions 2.24–2.25) and the Planned Milestone 3

Version 2.24.0's own text names a **target 7-module IA (Dashboard/Customers/Orders/Inventory/Finance/Reports/Settings)** and defers it explicitly: *"the target 7-module IA is planned as its own follow-up milestone, since demoting Production/Installation/Communication out of primary nav touches routing and cross-links from every other module and deserves separate review."* Version 2.25.0 delivered Milestone 2 (6-section nav: Dashboard/Sales/Inventory/Finance/Reports/Settings) but **the specific 7-module target described in Milestone 1 was never delivered as such** — what shipped is a close cousin (6 sections, not 7; Customers/Orders are folded into "Sales" rather than being their own top-level items). This is **not a defect** — it's a planned redesign that was completed in a different final shape than its own kickoff entry described, and nothing downstream references the original 7-item list as a contract. Flagged here only so a future session doesn't treat "Milestone 3" as still owed against the original 7-item description.

### 2.6 Audit-Driven Fix Cycles (Versions 2.26–2.30)

`PROJECT_AUDIT.md` (2026-07-21) raised five priorities; four were closed within days:

| Priority | Status |
|---|---|
| #1 Pagination rollout | ✅ Closed (2.26.0, 2.30.0) |
| #2 Dashboard resilience/KPI accuracy | ✅ Closed (2.27.0) |
| #3 CI-enforced import boundary | ✅ Closed (2.28.0) |
| #4 Doc sync (API_SPECIFICATION/DATABASE_DESIGN) | ✅ Closed (2.29.0) |
| #5 Purchasing/Marketing sequencing decision | ✅ Closed — both built (2.31.0, 2.32.0) |
| #6 Customer restore, Finance/Production sort params | 🟡 **Partially closed** — sort params fixed as part of 2.30.0's pagination fix; **customer restore-from-archive is still genuinely absent** (confirmed twice: `RELEASE_CHECKLIST.md` 2026-07-08 and again in `ROADMAP.md`'s 2.9.3 entry, both explicitly declining to build it as out-of-scope for the pass they were in) |
| #7 ESLint config | ❌ **Still missing** | No `.eslintrc*`/`eslint.config.*` committed; `npm run lint` is documented but non-functional |

### 2.7 What `MASTER_AUDIT_REPORT.md` Found That the Roadmap Never Named

The roadmap tracks *feature delivery* against its own plan extremely well. It does **not** track *commercial ERP completeness* against what a stone-fabrication business actually needs financially and operationally — because those items were never on the plan to begin with. This is the most important finding of this whole comparison: **the roadmap has essentially no gap against itself, but a real gap exists against "world-class ERP" that the roadmap never scoped in the first place.** The full list (credit control, quote-approval gates, order-cancellation cascades, credit notes, landed cost, commission tracking, seam-placement workflow, container/customs tracking, warranty/punch-list tracking, customer digital sign-off) is detailed in `MASTER_AUDIT_REPORT.md` and is carried forward into the execution plan below (§5–§7) rather than repeated in full here.

---

## 3. Everything Already Completed

- **All 14 modules** are real, tested, Clean-Architecture-complete implementations — confirmed by direct inspection, not just changelog claims. No stub or "coming soon" module exists anywhere (verified by grep across every module for TODO/FIXME/placeholder markers).
- **The entire original 10-module plan**, exactly as scoped in `PROJECT_ANALYSIS.md` §2.
- **Version 1.1 in full.**
- **CSV export, Assigned Manager picker, Customer Type picker** (the three Version 1.1/1.2 items that did eventually land, just later than their original version number implied).
- **Real third-party provider integrations** for Communication Center (Meta Graph API, SMTP/IMAP, Twilio) — genuinely wired, signature-verified, not mocked, even though this exceeds what most v1 ERPs ship for a comms module.
- **A CI pipeline with real architectural enforcement** (`.github/workflows/ci.yml`, `lint-imports`) — closed as of Version 2.28.0, resolving what was previously this project's own most-cited "the docs promise more than the code delivers" gap.
- **Documentation-vs-code sync** for `API_SPECIFICATION.md`/`DATABASE_DESIGN.md` — closed as of Version 2.29.0/2.30.0; both docs now self-report their own prior inaccuracies rather than hiding them, which is unusual and worth preserving as a practice.
- **Pagination correctness** across every list endpoint that matters (Version 2.26.0, 2.30.0).
- **Dashboard resilience** (`Promise.allSettled`, uncapped KPI aggregation) — Version 2.27.0.
- **The full Stone Fabrication Workflow Phase 1–2** (reservation, lifecycle, configurable stages, cut optimization, offcut management) — genuinely industry-specific work, not generic ERP boilerplate, and the single strongest recent addition to the product's real differentiation.

---

## 4. Everything Partially Completed

| Feature | What exists | What's missing |
|---|---|---|
| AI Sales Assistant | Full recommendation engine, human-approval workflow, 27 recommendation types | No real LLM provider ever called — `MockAIProvider` only, by explicit design |
| Executive IA redesign | 6-section consolidated nav, Executive Dashboard, Inventory Analytics | The originally-stated 7-module target description was never delivered in that exact shape (see §2.5) — likely fine as shipped, but worth a deliberate close-out decision rather than leaving it ambiguous |
| Task reminders | Full CRUD, recurrence, in-app notifications | No email/SMS delivery channel — still pull-based, in-app only |
| Multi-currency | `currency` field exists on Company/Order/Invoice | No FX-rate table or conversion logic anywhere — functions correctly only if a company never mixes currencies |
| Lead/Customer campaign attribution | Marketing's `campaign_id` (structured, FK-like) exists and is live-computed | The **older** free-text `crm_leads.campaign` and `crm_customers.advertising_campaign` fields still exist in parallel, unreconciled with the structured one (see §5) |
| Slab lot/block tracking | `Slab.lot_number` is a real, indexed field | No dedicated "Block" entity and no "same-lot slabs for this job" endpoint — the workflow exists as raw data, not as a supported user action |
| Cut Optimization yield tracking | Computes waste/utilization per run, can link to a quote/order item | No "planned vs. actual as-cut" distinction; Production itself never records a yield figure independently |
| Offcut/remnant resale | A real, independently reservable, sellable `Slab` row | No independent price — inherits the parent material's full list price |
| Site measurement / templating | `Order.MEASURING` status and a dedicated `OrderMeasurement` table both exist | No create/update endpoint to actually record as-built dimensions — the status exists, the workflow behind it doesn't |
| Quote versioning | Real version-forking on edit past `draft`, full audit trail of *that* a version was created | The audit diff only records `{new_version, parent_quote_id}`, not a field-level delta of *what* changed |
| Sealing/maintenance/warranty info | A cleaning-guide PDF can be attached per Material | No structured warranty duration, sealing schedule, or care-instructions field anywhere |

---

## 5. Everything Still Missing

Grouped by the two lenses that matter — "missing against the roadmap's own plan" and "missing against a world-class commercial ERP" (the latter drawn from `MASTER_AUDIT_REPORT.md`, cross-referenced here rather than re-derived):

**Missing against the roadmap's own stated plan:**
- Per-company configurable CRM pipeline stages & lead sources
- Role-scoped Dashboard/list views
- Email/SMS delivery for Task reminders
- Attachment thumbnails/previews
- Customer restore-from-archive
- Committed ESLint configuration
- Mobile client

**Missing against commercial-ERP/world-class expectations (never on the roadmap at all):**
- Quote discount/margin approval workflow
- AR aging, credit limits, credit holds
- Order-cancellation cascade (slab release, payment reversal)
- Credit notes / refund mechanism
- Landed cost on Purchase Orders, propagated to inventory
- Commission tracking
- Warranty / punch-list / defect tracking
- Returns / RMA
- Customer digital sign-off (quotes and job completion)
- Crew double-booking prevention (the check exists in code, is simply never called)
- Seam-placement / seam-approval workflow
- Container / shipment / customs tracking
- Real multi-currency (FX conversion)
- Supplier lead-time / reorder-point automation
- External accounting-system integration
- Bank reconciliation
- Postgres Row-Level Security
- httpOnly-cookie token storage

Full detail, evidence, and severity ratings for every item in this second group are in `MASTER_AUDIT_REPORT.md` §1–§7 and are not restated here to avoid duplicating that document; they are carried into the sequencing plan in §7.

---

## 6. Duplicate Features and Unnecessary Modules

**No unnecessary or redundant module was found.** All 14 installed modules serve a distinct, non-overlapping business function; `Reports` correctly has no tables of its own (it is a read-only cross-module aggregator by design, not an omission), and every `depends_on` declaration in a manifest reflects a genuine read-access need (e.g., `customer_portal` depending on five modules is appropriate for a module whose entire job is exposing a filtered view across all of them).

That said, three concrete instances of duplicated/dead functionality were found at the **field and data level**, which is worth flagging even though it doesn't rise to "unnecessary module":

1. **Parallel, unreconciled campaign-attribution fields.** `crm_leads` carries both a free-text `campaign` column *and* a structured `campaign_id` pointing at Marketing's `campaigns` table (confirmed: `backend/modules/crm/infrastructure/models/lead.py:18,24`). `crm_customers.advertising_campaign` is a third, entirely separate free-text field with no link to Marketing at all. A user filling out a Lead today can enter inconsistent data in two different "which campaign" fields on the same row, and Marketing's live-computed performance metrics only ever see the structured one. **Recommendation:** deprecate the free-text `campaign` field in favor of `campaign_id` (with a one-time backfill/migration mapping period), and either link `advertising_campaign` to the same structured entity or clearly document it as tracking something different (e.g., an *external* ad channel unrelated to an internal Marketing campaign).

2. **Dead frontend data: `module_permissions`.** `me()` (`frontend/lib/api/auth.ts:33`) fetches `module_permissions` from the backend on every session, and it is **never read anywhere else in the frontend** — confirmed by a zero-match grep across all of `app/` and `components/`. This is the exact payload the long-deferred frontend permission-gating feature (§5) would need to consume. **Recommendation:** either wire it into the permission-gating feature when that's finally built, or stop fetching it until it is — carrying dead data in every session response is a small but real waste.

3. **Structural (not wasteful) duplication between Quote and Order line items**, worth naming even though it's an intentional design choice, not a mistake: `QuoteSectionItem` and `OrderItem` carry near-identical fields (`unit_cost_price`, `line_total_cost`, `unit_sale_price`, etc.), and `Order` is created by deep-copying an accepted `Quote`'s line items rather than referencing them. This is the correct pattern for preserving an immutable, auditable snapshot of what was actually agreed — **do not "fix" this by making Order reference Quote data live** — but it does mean the two schemas can drift silently if one is changed without the other (already observed once: `MASTER_AUDIT_REPORT.md` §1's finding that `Invoice.subtotal_amount` is independently recomputed rather than copied, creating a latent divergence path). Any future schema change to either `QuoteSectionItem` or `OrderItem` should be checked against the other by habit.

---

## 7. Recommended Execution Order to Reach a World-Class ERP

The sequencing below merges three inputs: the roadmap's own unfinished 1.2 items, `MASTER_AUDIT_REPORT.md`'s business-value ranking, and this document's own architecture-risk read. It is organized into 10 phases. **Difficulty and time estimates (§8) assume a small, focused team of 1–2 senior full-stack engineers already familiar with this codebase's conventions** — consistent with the pace this project has itself demonstrated (most single-version deliveries in `CHANGELOG.md` read as one to a few focused sessions each, with full test coverage).

### Phase 1 — Quick Wins & Safety Nets
Crew double-booking prevention (the query already exists — this is wiring, not building); `alembic check` added to CI; CORS methods/headers tightened from wildcard; campaign-field consolidation (§6.1); `module_permissions` dead-data resolution (§6.2).

### Phase 2 — Financial Control Foundations
Quote discount/margin approval workflow; AR aging + credit limit/credit hold; order-cancellation cascade (slab release + payment-status reversal); credit notes/refund mechanism. **This is the single highest-business-value phase in the entire plan** — every item in it addresses direct, quantifiable financial risk identified in `MASTER_AUDIT_REPORT.md` §1–§2.

### Phase 3 — True Cost & Margin Pipeline
Landed cost fields on Purchase Order lines (freight/customs/duty); cost propagation from receiving into `Slab`; recompute margin/COGS reporting to use real cost instead of the frozen quote-time estimate.

### Phase 4 — Customer Trust & Compliance
Customer digital sign-off on quotes; a real signature/acceptance requirement before an installation job can be marked complete; warranty period + punch-list/defect tracking; returns/RMA for delivered stone.

### Phase 5 — Stone Industry Deepening
Seam-placement/approval workflow; a real as-built re-measurement endpoint (closing the "cosmetic MEASURING status" gap); container/shipment/customs tracking in Purchasing; independent pricing for offcuts/remnants; actual-vs-quoted yield tracking fed back from Production into Cut Optimization's history.

### Phase 6 — CRM/Sales Completeness (closing out Version 1.2)
Per-company configurable pipeline stages & lead sources (bringing CRM in line with the pattern Production already has); role-scoped Dashboard/list views; a `credit_terms`/`payment_terms` field on Customer, consumed by Sales/Finance; a hard duplicate-customer check at creation time (not just AI-advisory).

### Phase 7 — Commission & External Bookkeeping Bridge
Sales-rep commission tracking; an export/integration path to at least one external accounting system (even a structured CSV/API export is a meaningful start); bank reconciliation (statement import + matching against recorded payments).

### Phase 8 — Security & Architecture Hardening
httpOnly-cookie migration for refresh tokens (staff and Customer Portal both); Postgres Row-Level Security as the real second tenancy-isolation layer; mandatory Redis for the rate limiter and token-revocation denylist (removing the silent in-memory fallback) ahead of any multi-instance deployment; evaluation of moving the event bus to genuinely async dispatch (Celery-backed) if/when event-handler workload grows.

### Phase 9 — UX & Developer-Experience Polish
Committed ESLint config; attachment thumbnails/previews; a real icon library (per `UI_UX_GUIDELINES.md`'s own stated intent); tablet-width collapsed sidebar; frontend permission gating (finally consuming `module_permissions`); customer restore-from-archive; email/SMS delivery for Task reminders.

### Phase 10 — Mobile Client
Build the first mobile client against the existing, already-versioned API — the last unbuilt phase of the original frozen architecture (`PROJECT_ANALYSIS.md` Phase 9).

---

## 8. Difficulty and Time Estimates Per Remaining Phase

| Phase | Difficulty | Estimated Time | Primary Risk Driver |
|---|---|---|---|
| 1 — Quick Wins & Safety Nets | **Easy** | 3–5 developer-days | Low — mostly additive wiring |
| 2 — Financial Control Foundations | **Hard** | 3–4 weeks | Touches the most heavily-used write paths in the system (see §9) |
| 3 — True Cost & Margin Pipeline | **Medium–Hard** | 2–3 weeks | Changes numbers already relied on by Reports/Dashboard KPIs |
| 4 — Customer Trust & Compliance | **Medium** | 2–3 weeks | Mostly additive; low collision risk with existing flows |
| 5 — Stone Industry Deepening | **Medium–Hard** | 3–4 weeks | Seam-placement and container-tracking are genuinely new domain concepts, not extensions of existing ones |
| 6 — CRM/Sales Completeness | **Medium** | 2–3 weeks | Configurable pipeline stages touches every hardcoded status check across CRM |
| 7 — Commission & Accounting Bridge | **Medium (commission) / Hard (accounting integration)** | 3–5 weeks combined | External integration scope is open-ended until a target system is chosen |
| 8 — Security & Architecture Hardening | **Hard** | 3–5 weeks | Highest technical risk in the plan — see §9 |
| 9 — UX & DX Polish | **Easy–Medium** | 1–2 weeks | Low; independent, parallelizable items |
| 10 — Mobile Client | **Hard (XL)** | 8–12+ weeks | Effectively a second frontend; not a "phase," a program |

**Sequencing note:** Phases 1, 4, 5, 6, and 9 have no meaningful dependency on each other and can run in parallel with a second engineer. Phase 2 should be substantially complete before Phase 3 (cost accuracy is far more valuable once cancellations/refunds are also handled correctly — otherwise "accurate margin" can still be corrupted by an unhandled cancellation). Phase 8's RLS work should land before Phase 10 (mobile) begins, since a second client surface is exactly when a missed `company_id` filter becomes more likely to matter.

---

## 9. Features That Could Break Existing Code

Ranked by blast radius — how much currently-stable behavior each touches:

| Change | Breaking-Risk Level | Why |
|---|---|---|
| **Postgres Row-Level Security (Phase 8)** | 🔴 **Very High** | Requires `SET LOCAL app.current_company_id` wired into every request's transaction lifecycle in `core/db/session.py` — the single most shared piece of infrastructure in the entire backend. A missed or misordered `SET LOCAL` call could either silently fail to protect a query (no improvement) or incorrectly lock out a legitimate query (a hard outage). Must be rolled out with a shadow/audit mode before enforcement is turned on. |
| **httpOnly-cookie token migration (Phase 8)** | 🔴 **Very High** | Touches the authentication flow for *two independent identity systems* (staff and Customer Portal) simultaneously, every API call's credential-attachment mechanism, CORS configuration (`allow_credentials`), and the frontend's refresh/retry logic. A partial migration (one client fixed, one not) would break login entirely for whichever client is out of sync. |
| **General ledger / double-entry accounting, if ever added to Finance** | 🔴 **Very High** | Not in the recommended phases above (deliberately deferred as a separate, larger product decision — see §10), but flagged here because if it is ever pursued, it would restructure Finance's core data model and every downstream consumer (Reports' finance analytics, the Dashboard, Invoice/Payment use cases) simultaneously. |
| **Real multi-currency / FX conversion (Phase 3-adjacent)** | 🟠 **High** | Every place that currently naively sums `total_final`/`amount_paid` across orders/invoices (Reports, Dashboard KPIs) would need simultaneous updates, or aggregate figures would silently misrepresent mixed-currency data during the transition. |
| **Order-cancellation cascade (Phase 2)** | 🟠 **High** | Changes real, physical inventory state (slab release) as a side effect of a status change that previously had no downstream effect at all. Existing operational habits ("cancelling doesn't do anything to the slab, so I'll manually release it") would need to change in lockstep with the code, or double-releases become possible. |
| **Quote discount/approval gate (Phase 2)** | 🟡 **Medium** | If the approval threshold defaults too low, it could block legitimate, previously-frictionless workflows the sales team relies on daily. Must ship with a deliberately permissive default threshold and a clear rollout communication, not a silent tightening. |
| **Per-company configurable pipeline stages (Phase 6)** | 🟡 **Medium** | The 14 CRM statuses are currently referenced by hardcoded string comparisons in multiple places (Dashboard KPI logic, Reports). Making them configurable requires finding and updating every one of those comparisons, or some existing KPI/report logic will silently stop matching real data. |
| **Circular FK resolution (`crm_customers`/`crm_contacts`)** | 🟡 **Medium** | A schema migration touching two of the most-referenced tables in the system; low functional risk if done carefully, but any migration on these tables warrants full regression coverage before merge. |
| **Async/Celery event bus (Phase 8, optional)** | 🟡 **Medium** | Changes the current guarantee that an event's persistence shares the publishing transaction. Every future event subscriber would need to be written against weaker consistency assumptions than today's synchronous, same-transaction model provides. |
| **Landed cost propagation into `Slab` (Phase 3)** | 🟢 **Low–Medium** | Additive schema change (a new cost field), but changes the *number* that margin reports have always shown — stakeholders should be told margin figures will visibly change (likely downward, toward more accurate) the day this ships. |
| Everything in Phases 1, 4, 5 (customer sign-off, warranty tracking, seam approval, container tracking), 6 (role-scoped views, credit terms field), 7 (commission), 9 | 🟢 **Low** | All are additive — new tables/fields/endpoints with no modification to existing write paths' current behavior. |

---

## 10. Features That Should Never Be Changed — Already Stable

These are load-bearing, heavily-tested, and correctly designed. Changing them without a very specific, well-justified reason would introduce risk for no proportionate benefit:

- **The module registry contract** (`ModuleManifest`, `core/module_registry/contracts.py`/`registry.py`) — proven across 14 modules with zero exceptions; this is the platform's most fundamental abstraction and the one piece every other design decision assumes is fixed.
- **The core/module import boundary rule itself** — now enforced by both an AST test and a real CI-gated `import-linter` contract (Version 2.28.0). This is the architecture's single most important guarantee and is finally backed by automation, not discipline alone.
- **The `GUID` TypeDecorator** (`core/db/mixins.py`) — the mechanism that lets the entire test suite run against SQLite while production runs Postgres. Touching this affects every table in the system simultaneously.
- **The RBAC permission-suffix convention** (`"<module>:<resource>:<action>"`, action-tier mapping in `core/rbac/permissions.py`) — consistent across all 14 modules; verified with zero gaps in the most recent audit. A new module should follow it, not question it.
- **The audit-log + event-publish discipline** on every write use case — verified 100% consistent by scripted cross-check across every module. This is a rare example of a cross-cutting convention that is genuinely, not just nominally, followed everywhere.
- **The Clean Architecture layering** (`domain → application → infrastructure → presentation`) inside every module — consistent enough across 14 independently-built modules that a developer who learns one module can navigate all of them. Preserve this even under time pressure.
- **The cursor-pagination contract** (`next_cursor`, opaque base64 offset token) — now correctly implemented end-to-end after two dedicated fix cycles (2.26.0, 2.30.0). Any new list endpoint should copy this exactly, not invent a variant.
- **`apiRequest`/`ApiRequestError` on the frontend** (`lib/api-client.ts`) — the single, consistent typed-fetch pattern all 16 per-module API wrapper files already follow correctly.
- **The i18n `LocaleProvider`/deep-merge-fallback pattern** — az/ru/en are at exact 1,538-key parity today; this discipline is worth protecting explicitly as new features land, since key-parity drift is easy to introduce silently.
- **The Catalog slab lifecycle state machine** (`SLAB_STATUS_*` transitions, `core/…/value_objects.py`) — this is the most heavily fabrication-specific, heavily tested piece of business logic in the whole system (reservation, offcut lineage, scrap, lifecycle). It has been extended twice (Phase 1 and 2 of the Stone Fabrication Workflow) without ever being restructured — a strong signal it was designed correctly the first time. Extend it; don't rewrite it.
- **The Cut Optimization nesting algorithm** (`modules/cut_optimization/domain/cutting_algorithm.py`) — pure, framework-free, unit-tested in isolation (10 dedicated algorithm tests covering placement, kerf, rotation, multi-shelf, and 100%-utilization edge cases). This is exactly the kind of code that should remain untouched except for genuine algorithmic improvements, never casual refactoring.
- **The CI pipeline itself** (`.github/workflows/ci.yml`) — simple, fast, and finally doing what the architecture docs always claimed it did. Resist the urge to make it more elaborate than the two jobs it currently runs unless a specific new gate is genuinely needed.

---

## 11. Closing Assessment

G-STONE ERP has executed its own roadmap with unusual fidelity — every module it set out to build exists, is tested, and is in real use. The gap to "world-class" is not a gap in engineering discipline; it is a gap in **scope that was never on the plan**, concentrated almost entirely in money-handling controls (credit, approvals, refunds, true cost) and a handful of stone-industry-specific workflows (seams, containers, real templating) that a generic ERP roadmap would never have surfaced on its own. Phases 2 and 5 of §7 are where the highest-value work remaining actually lives — not in finishing the original roadmap, which is essentially done, but in extending it into territory it never covered.

*End of report. No code was written or modified. No existing file was changed.*
