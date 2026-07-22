# G-STONE ERP — Master Audit Report

**Auditor role:** Independent ERP Auditor (external, commercial-product review)
**Scope:** Full codebase, `backend/` + `frontend/`, as of commit `8fc6506` (Version 2.35.0, 2026-07-22)
**Method:** Direct source review — domain entities, use cases, API routes, database models — cross-checked against real stone-fabrication-industry and general-ERP practice. No code was modified. No refactoring suggestions are included; findings are business-risk and feature-gap oriented only.

---

## Executive Summary

G-STONE ERP is a technically well-built platform — clean module boundaries, consistent audit/event discipline, no SQL injection surface, solid RBAC. **That engineering quality is not in question here.** What this audit finds is a different thing: **as a commercial ERP for a stone fabrication business, several money-handling and industry-specific workflows are either missing outright or exist only as a cosmetic field with no enforcing logic behind it.**

The single clearest pattern across this audit: **a status field or a database column often exists, but the business rule that should sit behind it does not.** A quote has a `valid_until` date that nothing checks. An order has a `MEASURING` status but no way to actually record a re-measurement. An installation photo can be tagged `"signature"` but nothing requires one before a job is marked complete. A crew-conflict query exists in the repository layer and is never called. This is a recurring shape of gap, not a collection of unrelated bugs — and it means a surface-level review of "does the field exist" would badly understate the real risk.

The five findings with the highest business impact, in one line each:

1. **No credit control** — a customer can be invoiced and re-ordered against indefinitely with no visibility into what they already owe.
2. **No quote-discount approval gate** — any rep can give away unlimited margin with zero oversight or record of why.
3. **Order cancellation doesn't release reserved material or reverse payment** — cancelled orders leave slabs permanently "reserved" and deposits with no refund path.
4. **Purchasing cost never reaches true landed cost, and never reaches inventory at all** — every margin number reported anywhere in the system is built on an understated, quote-time-frozen cost figure.
5. **No container/customs/import tracking, and no seam-placement workflow** — the two stone-industry-specific gaps most likely to generate real customer disputes and real import friction, in a business that (per the country-of-origin field's own use) sources internationally.

---

## Priority Matrix — Ranked by Business Value

| # | Finding | Category | Impact | Est. Effort |
|---|---|---|---|---|
| 1 | No AR aging / credit limit / credit hold — orders never blocked by unpaid balance | Business logic | 🔴 Critical — bad-debt exposure | M |
| 2 | No quote discount/margin approval workflow | Business logic | 🔴 Critical — uncontrolled margin leakage | S–M |
| 3 | Order cancellation doesn't release slabs or reverse payment | Business logic | 🔴 Critical — inventory + financial integrity | M |
| 4 | No credit notes / refund mechanism anywhere in Finance | Missing ERP feature | 🔴 Critical — no way to correct overpayment/cancellation | M |
| 5 | Purchasing cost ≠ landed cost, and never reaches `Slab`/inventory at all | Business logic | 🔴 Critical — every margin/profit number in the system is unreliable | M–L |
| 6 | No commission tracking anywhere in the codebase | Missing ERP feature | 🟠 High — manual/disputed rep payouts | M |
| 7 | Container/shipment/customs tracking completely absent | Stone workflow | 🟠 High — no system of record for imported stock | M |
| 8 | Seam layout / seam-approval workflow absent | Stone workflow | 🟠 High — top customer-dispute driver in countertop fabrication | M |
| 9 | Site "measuring" step is cosmetic — no way to re-enter as-built dimensions | Stone workflow | 🟠 High — fabrication still runs off quote-time estimates | S–M |
| 10 | Crew double-booking not prevented (query exists, never called) | UX / business logic | 🟠 High — real scheduling collisions, cheap fix | S |
| 11 | No warranty period / punch-list / defect tracking post-installation | Missing ERP feature | 🟠 High — undocumented warranty claims, legal exposure | M |
| 12 | No customer digital sign-off on quotes or job completion | Business logic / UX | 🟠 High — disputes over "did the customer actually agree to this" | M |
| 13 | No returns/RMA mechanism for delivered stone | Missing ERP feature | 🟠 High — no defined path for a damaged/wrong-color delivery | M |
| 14 | Auth tokens (staff + customer) stored in `localStorage` | Security | 🟠 High — XSS exfiltration exposure | S–M |
| 15 | Postgres Row-Level Security not implemented (single-layer tenant isolation) | Security / Database | 🟠 High — no backstop if a future query misses `company_id` | M |
| 16 | Multi-currency is cosmetic (string field, no FX conversion) | Database / Business logic | 🟡 Medium — real risk only if any company transacts cross-currency | M |
| 17 | No customer credit terms (Net 30 / COD) field anywhere | Missing ERP feature | 🟡 Medium | S |
| 18 | No supplier lead time / reorder-point automation; every PO fully manual | Missing ERP feature | 🟡 Medium | M |
| 19 | Offcut/remnant has no independent resale price (inherits parent material price) | Stone workflow | 🟡 Medium | S |
| 20 | No actual-yield-vs-quoted-yield feedback loop in Production | Stone workflow | 🟡 Medium | S–M |
| 21 | Duplicate-customer detection is AI-advisory only; no hard check at creation | Business logic | 🟡 Medium | S |
| 22 | No external accounting-system integration (QuickBooks/1C/SAP/etc.) | Missing ERP feature | 🟡 Medium — likely a parallel, unreconciled bookkeeping system | L |
| 23 | No bank reconciliation — "payment received" is an unverified manual flag | Missing ERP feature | 🟡 Medium | M |
| 24 | Edge profile is a generic line-item type, not structured data | Stone workflow | 🟢 Low–Medium | S |
| 25 | Breakage/scrap has no reason code (transit vs. fabrication vs. other) | Stone workflow | 🟢 Low | S |
| 26 | No frontend permission gating (viewer sees write buttons, gets 403 on submit) | UX | 🟢 Low — backend is authoritative, so this is UX-only | S |
| 27 | No quarry/certification tracking (only country-of-origin) | Stone workflow | 🟢 Low | S |
| 28 | Event bus is synchronous/in-process; rate limiter & token denylist fall back to in-memory without Redis | Architecture | 🟢 Low at current scale, real risk if ever multi-instance | M |
| 29 | Migration chain not verified in CI (`alembic check` not wired in) | Database | 🟢 Low | S |
| 30 | ~86 free-text fields with no `max_length` | Database | 🟢 Low | S |

---

## 1. Business Logic Gaps

### 1.1 No quote discount/approval workflow — 🔴 Critical
`UpdateQuoteStatusUseCase` validates only the status transition graph and slab availability; it never inspects `discount_type`/`discount_value`/`profit_margin_pct`. Sales exposes exactly one write permission, `sales:quotes:write` — there is no separate "requires manager sign-off above X% discount" concept, and no such check exists in `totals.py` either. **Any user who can create a quote can send or accept it at any discount, with no record of why, no second approver.** For a business where quotes are the main lever on margin, this is the single largest uncontrolled leak in the system.

### 1.2 No AR aging, credit limit, or credit hold — 🔴 Critical
`Customer` carries no `credit_limit` field. `Invoice.status` includes `overdue`, but it is a manually-set flag, not a computed 30/60/90-day aging bucket — nothing recalculates it. Nothing in Orders checks a customer's outstanding balance before letting staff create another order. **A customer who owes money on three unpaid invoices can be sold a fourth order with no warning anywhere in the system.**

### 1.3 Order cancellation has no downstream effects — 🔴 Critical
`ORDER_CANCELLED` is published but has **zero subscribers** anywhere in the codebase. Contrast this with Quote rejection, which does explicitly release reserved slabs (`_release_slabs`) — Orders has no equivalent. A cancelled order leaves its slabs `reserved` indefinitely, and any deposit paid has no refund path (see 2.2). This is a direct financial-integrity and inventory-integrity bug in the business process, not just a missing nicety.

### 1.4 Purchasing cost never reaches inventory or true margin — 🔴 Critical
`PurchaseOrderLine.unit_cost` is raw supplier price only — no freight/customs/duty field exists anywhere in Purchasing. Worse: `ReceivePurchaseOrderLineUseCase` creates the resulting `Slab` **without ever passing a cost value at all** — `Slab` has no cost field. Every margin figure reported anywhere downstream (`Quote.profit_margin_pct`, `Order.total_profit`, Reports' finance analytics) is therefore the **quote-time estimate**, frozen at order creation, never reconciled against what was actually paid to acquire the material. For an imported-stone business where freight/customs commonly represents a meaningful fraction of landed cost, every profitability number in the system is systematically understated in accuracy, not just imprecise.

### 1.5 Order line items can't be formally changed post-acceptance — 🟠 High
There is no endpoint to edit an `OrderItem`'s quantity/price once an order exists (only `production_status`/`installation_status`/`notes` are patchable) — so silent overwrites are prevented, but so is any legitimate change order. If a customer requests a scope change mid-fabrication, there is no way to record it in the system at all; it would have to happen entirely off-system.

### 1.6 Duplicate-customer detection is advisory-only — 🟡 Medium
`CreateCustomerUseCase` inserts unconditionally — no unique constraint on phone or email, no lookup before insert. The only duplicate detection anywhere is a post-hoc, dismissible AI recommendation. A busy front-desk workflow will accumulate duplicate customer records over time with nothing structurally preventing it.

### 1.7 No formal partial-fulfillment/backorder concept — 🟡 Medium
This is architecturally consistent (each line item points to one specific, non-fungible slab, not a stockable quantity), but it means "5 ordered, 3 available" isn't a modeled business scenario at all — acceptance either fully succeeds or fails outright on the first unavailable slab, with no partial-acceptance path.

---

## 2. Missing ERP Features

### 2.1 No credit notes or refund mechanism — 🔴 Critical
A repo-wide search for `credit_note`/`refund` returns nothing relevant anywhere in the backend. Invoicing is strictly forward-only: cancelling an invoice just stops it — `amount_paid` is never reversed. There is **no way in the system** to correct an overpayment or refund a cancelled order's deposit. This has to happen entirely outside the ERP today (cash, bank transfer, informal spreadsheet), which is both an operational gap and a bookkeeping-accuracy risk.

### 2.2 No deposit-at-order-time flow — 🟠 High
`Payment`'s own docstring anticipates "deposit, progress, final" payments, but `CreateInvoiceUseCase` only allows invoicing once an order reaches `ready`/`delivered`/etc. — a customer **cannot be invoiced or pay a deposit before production starts**, despite this being one of the most standard practices in custom fabrication (material and labor commitment before cutting begins).

### 2.3 No commission tracking — 🟠 High
Zero matches anywhere in the codebase for `commission`. No `Order`/`Quote` field distinguishes the selling rep from `Customer.assigned_manager_id`. If reps are commissioned — typical in a gallery/showroom sales model — this is entirely unsupported and pushed to spreadsheets, with the attendant dispute risk.

### 2.4 No warranty / punch-list / defect tracking — 🟠 High
No warranty-period field exists on `Order` or `StoneMaterial`. No punch-list/defect entity exists anywhere in Installation. A photo can be *tagged* `"damage"`, but that's a caption on an image, not a tracked defect with severity/resolution/follow-up. Post-installation issues have no system home.

### 2.5 No returns/RMA — 🟠 High
No entity, no status, no workflow for a customer rejecting delivered stone (wrong color, chipped, doesn't match sample). The closest concept, `completion_status` (pending/delivered/accepted), tracks handover, not rejection.

### 2.6 No credit terms on the customer record — 🟡 Medium
No `payment_terms`/`Net 30`/COD concept anywhere — confirmed by a zero-match grep across the entire backend. Nothing downstream could consume such a value even if it existed.

### 2.7 No supplier lead time or reorder automation — 🟡 Medium
Every purchase order is fully manual; no reorder-point or low-stock trigger exists anywhere in Purchasing. `expected_delivery_date` is free-typed per PO, not derived from any supplier default.

### 2.8 No supplier performance tracking — 🟡 Medium
`Supplier` has no on-time-delivery or rejection-rate field; nothing computes such a metric from the receiving data that does exist.

### 2.9 No external accounting-system integration — 🟡 Medium
Zero references to QuickBooks/1C/SAP/Xero or any generic accounting-export mechanism anywhere in the backend. Given the system also has no general ledger of its own (§4.1), a business using this ERP for operations still needs a **separate** system for statutory bookkeeping, with no reconciliation bridge between the two — a real, ongoing operational cost that compounds the "no GL" finding.

### 2.10 No bank reconciliation — 🟡 Medium
"Payment received" is a manually-entered `Payment` row with a free-text reference note — no bank feed, no statement import, no matching. This is standard for a Phase-1 ERP but should be flagged as a real gap before this system is trusted as the sole source of truth for cash position.

---

## 3. Architecture Risks

*(Full technical detail was covered in this project's own `PROJECT_AUDIT.md`; summarized here strictly for business-risk relevance.)*

### 3.1 Event bus is synchronous, in-process — 🟢 Low today, real ceiling later
A slow or failing event handler runs inline within the publishing request's response cycle. At 3-company scale this is invisible; it becomes a real availability risk the moment event-handler work (e.g., any future AI/document-processing subscriber) gets heavier.

### 3.2 Rate limiter and token-revocation state are in-memory, not distributed — 🟢 Low today
Both fall back silently to in-process state when Redis is unreachable. This is fine for a single backend instance; it silently stops working correctly (rate limits and "logout everywhere" both become per-instance rather than global) the moment this is ever deployed as more than one instance.

### 3.3 Single points of business-rule enforcement — 🟡 Medium, cross-cutting
This is the pattern named in the Executive Summary: several critical business rules (quote discount limits, credit checks, crew-conflict checks) have a data model that could support them but no enforcing code path. This isn't a single bug — it's a recurring gap between "the schema anticipated this" and "the use case actually checks it," and it's worth treating as one finding for prioritization purposes, since fixing the pattern (a habit of "does every state-changing use case enforce every business rule its own fields imply") will catch more than any one fix below it.

---

## 4. Database Issues

### 4.1 No general ledger / chart of accounts — 🔴 Critical (context for §2.9)
Finance consists solely of `Invoice`, `InvoiceLine`, `Payment`, and `Expense` tables. There is no journal-entry/debit-credit model and no trial-balance construct anywhere. This is fine as an invoicing tool; it is not a bookkeeping system, and should not be marketed or relied upon as one without a clear-eyed understanding of that boundary.

### 4.2 Currency is a bare string with no FX table — 🟡 Medium
`Company.currency`, `Order.currency`, `Invoice.currency` are all independent `String(3)` columns (default `"AZN"`) with no exchange-rate table anywhere in the codebase. Reports' revenue/profit KPIs sum `total_final` across orders and only bucket by currency **afterward**, for display — nothing stops or reconciles genuinely mixed-currency data if it occurs. Real risk only if any company actually invoices in more than one currency; otherwise cosmetic.

### 4.3 No Postgres Row-Level Security — 🟠 High (see §5.2)
### 4.4 Circular FK between `crm_customers` and `crm_contacts` — 🟢 Low
Works today via nullable columns; flagged by SQLAlchemy as a table-sort warning that may become a hard error on a future major-version upgrade.

### 4.5 No `max_length` on ~86 free-text fields — 🟢 Low
Defense-in-depth gap, not an active exploit path (no raw SQL formatting exists anywhere in the codebase).

### 4.6 Migration chain unverified in CI — 🟢 Low
The test suite builds its schema via `Base.metadata.create_all()` directly from live models, bypassing the Alembic migration chain entirely — a green CI run does not, by itself, prove the migration chain matches the models. `alembic check` exists and passes when run manually but isn't wired into CI.

---

## 5. Security Issues

### 5.1 Auth tokens (staff and customer) stored in `localStorage` — 🟠 High
Both access and refresh tokens, for both staff and the separate Customer Portal identity system, are stored in `localStorage`. This is an XSS-exfiltration exposure — low urgency only because no active XSS vector is currently known in the app, but the exposure itself is real and worth resolving before any surface with less-trusted input (e.g. rich-text notes, uploaded document rendering) is added.

### 5.2 No Postgres Row-Level Security — 🟠 High
The architecture's own design docs describe RLS as a second, defense-in-depth tenant-isolation layer; it was never implemented. Every tenant boundary in production today rests entirely on consistent `WHERE company_id = ...` filtering in each repository — verified thorough on inspection, but with **no structural backstop** if a future query is written without it.

### 5.3 CORS methods/headers wildcarded — 🟢 Low
`allow_methods`/`allow_headers` are both `["*"]`. Origins are correctly restricted and environment-configurable, so actual exposure is low, but this is looser than necessary.

### 5.4 Rate limiting / revocation state not distributed — see §3.2.

### 5.5 What's genuinely solid (stated for balance)
No SQL injection surface anywhere (100% parameterized SQLAlchemy). RBAC (`require_permission`) is enforced on every write endpoint across every module, correctly excepting only the three signature-verified public webhook receivers. Company-scoping was checked across CRM/Sales/Finance/Production repositories with no gaps found. The app refuses to boot outside development with placeholder JWT/encryption-key secrets still in place. Refresh-token revocation ("logout everywhere") is real and tested.

---

## 6. UX Problems

### 6.1 Crew double-booking is not prevented — 🟠 High
`InstallationJobRepository.list_for_crew_on_date` exists specifically to support a conflict check and is **never called anywhere outside its own definition**. Assigning a crew to a job does no lookup against that crew's other scheduled jobs. This is a cheap fix (the query already exists) with real operational consequence (double-booked crews mean missed or rescheduled customer appointments).

### 6.2 No customer digital sign-off — 🟠 High
Quote acceptance is staff clicking a status button on the customer's behalf — there is no signature/token/portal-based customer acceptance of a quote's price. At installation completion, a photo can be *tagged* `"signature"`, but attaching one is entirely optional and nothing blocks marking a job `completed` without it. For a business with real money and real disputes at stake, "the customer agreed to this" currently has no evidentiary trail.

### 6.3 No frontend permission gating — 🟢 Low
A viewer-role user sees the same Create/Edit/Archive controls as an owner and only discovers the restriction via a 403 on submit. Not a security hole (backend RBAC is authoritative and verified solid), but a real day-to-day friction point for lower-privileged roles.

### 6.4 Design-system deviations — 🟢 Low
No committed icon library despite the written design guideline calling for one (hand-rolled inline SVGs across ~8 components); tablet breakpoint (768–1023px) gets the same full slide-over drawer as phone width rather than the icon-only collapsed sidebar the guidelines specify; mobile nav drawer has no keyboard focus trap.

### 6.5 No attachment thumbnails/previews — 🟢 Low
Images in the Attachments card render as filenames only, not inline previews — a real quality-of-life gap for a business whose day-to-day work involves product/site photos.

---

## 7. Stone Industry Workflow Gaps

*(This is the section most specific to G-STONE's actual business, and arguably the most commercially consequential category alongside §1–2.)*

### 7.1 No container/shipment/customs tracking — 🟠 High
A grep for `container`/`bill of lading`/`customs` across Purchasing and Catalog returns **zero matches**. `PurchaseOrder` and `GoodsReceipt` carry only PO number, supplier, expected delivery date, and received quantity — nothing for container number, bill of lading, or customs/import documentation. For a business sourcing stone internationally (the `country_of_origin` field on `Material` confirms this is expected), this is a real operational hole: no system record of what's in transit, no way to reconcile a container's contents against what actually arrives, no home for import paperwork.

### 7.2 Seam layout / seam-approval workflow is completely absent — 🟠 High
A grep for `seam` across the entire backend returns nothing relevant. Cut Optimization computes generic bin-packing/nesting placements with no seam-specific concept. In real countertop fabrication, seam *placement* (not just yield) is one of the most common sources of customer dissatisfaction — customers care where a seam falls on their counter, not just how much waste it produces. There is no drawing/approval step for this at all, distinct from the cut-optimization nesting the system already has.

### 7.3 The "measuring" step is cosmetic — 🟠 High
`Order` has a dedicated `MEASURING` status and a distinct `OrderMeasurement` table — but `OrderMeasurement` rows are only ever a verbatim deep-copy of the quote's original measurements at order-creation time. There is **no create/update endpoint** to actually record as-built dimensions from a real site template visit. The status exists; the workflow behind it doesn't. Production therefore still fabricates against quote-time estimates, which is a well-known source of on-site fitting errors in this industry.

### 7.4 Offcut/remnant has no independent resale price — 🟡 Medium
An offcut becomes a real, independently-trackable, sellable `Slab` row — genuinely good coverage — but `PriceListEntry` is keyed only by `material_id`, so a remnant inherits its parent material's full list price rather than having its own (typically discounted) resale price. Selling a remnant at a fair price today requires manually overriding the unit price on every single line item.

### 7.5 No actual-vs-quoted yield tracking — 🟡 Medium
`CutOptimizationRun` computes waste/utilization per run and can link to a quote or order item, but nothing distinguishes a "planned" run from an "actual as-cut" run, and Production itself never records a waste/yield figure at all. There's no feedback loop telling the business whether real fabrication is tracking to the estimates quotes are built on.

### 7.6 Edge profile is not structured data — 🟡 Medium
`edge_profile` exists only as a generic line-item *type* (priced per linear meter, like any other service charge) — there is no selectable edge-profile attribute (bullnose, ogee, eased, etc.) captured as structured data anywhere, and no equivalent structured field for finish at the order-line level (finish is only implicit via the Material SKU chosen). This limits both customer-facing selection UX and any future analytics on which profiles/finishes actually sell.

### 7.7 Breakage/damage has no reason code — 🟢 Low
`Slab` has a terminal `SCRAP` status reachable from nearly any state, with a docstring literally acknowledging "a slab can break at any stage" — but there's no structured distinction between damaged-in-transit, broken-in-fabrication, or any other write-off cause, only a free-text notes field. This matters for a business trying to determine whether breakage losses are a shipping problem, a handling problem, or a cutting problem.

### 7.8 Lot/block tracking exists but isn't a first-class concept — 🟢 Low
`Slab.lot_number` is a real, indexed field — genuinely present, unlike most of this section. But it's a bare string with no dedicated "Block" entity and no dedicated "same-lot slabs for this job" endpoint — grouping slabs from the same lot for large-job color consistency depends on a caller manually filtering by this string rather than the system actively supporting the workflow.

### 7.9 No quarry name or certification tracking — 🟢 Low
`country_of_origin` is real and searchable, but there's no dedicated quarry-name field, and no structured certification tracking (e.g., radioactivity/environmental certification sometimes required for natural stone) — at best a certificate could be shoehorned into the generic material-document upload, but "certificate" isn't even one of the three defined document types today.

### 7.10 Sealing/maintenance/warranty info is unstructured — 🟢 Low
No warranty field exists on `Order` or `Material`. A cleaning-guide PDF can be attached per material, but there's no structured sealing schedule, warranty duration, or care-instructions text field — everything here depends on someone actually uploading and a customer actually reading a PDF.

---

## Recommended Sequencing (business value, not effort, drives this order)

**Do first — direct exposure to money or legal risk:**
1. Quote discount/approval gate (§1.1)
2. Order-cancellation slab release + payment reversal (§1.3)
3. Credit notes/refund mechanism (§2.1)
4. AR aging + credit limit/hold (§1.2)
5. Crew double-booking check — the query already exists (§6.1)

**Do next — closes the biggest stone-industry-specific dispute risks:**
6. Seam placement/approval step (§7.2)
7. Real as-built re-measurement endpoint (§7.3)
8. Customer digital sign-off on quotes and job completion (§6.2)
9. Warranty/punch-list tracking (§2.4)
10. Container/customs tracking for imported stock (§7.1)

**Do after — closes real but lower-urgency operational and financial-accuracy gaps:**
11. Landed cost on Purchase Orders, propagated to `Slab.unit_cost` (§1.4)
12. Commission tracking (§2.3)
13. Returns/RMA (§2.5)
14. Credit terms field + downstream consumption (§2.6)
15. Remnant independent pricing (§7.4)

**Hardening, not urgent at current scale:**
16. localStorage → httpOnly cookie token migration (§5.1)
17. Postgres RLS (§5.2)
18. Multi-currency real conversion, if any company actually needs it (§4.2)
19. External accounting-system export/integration (§2.9)
20. Everything in §6.3–6.5 and §7.6–7.10 (polish-tier, real but lower stakes)

---

*End of report. No code was modified during this audit.*
