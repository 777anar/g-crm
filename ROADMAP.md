# G-STONE ERP — Product Roadmap

_Date: 2026-06-30_
_Status: CRM Version 1.0 is frozen as of commit `bec2def`. No new business features are being added until this roadmap is approved._

This is a product-perspective review of the application as it stands, and a proposal for what comes next, split into three horizons: **1.1** (polish the frozen CRM), **1.2** (deepen the CRM into a daily operating tool), and **2.0** (the first new ERP module beyond CRM, per the modular architecture frozen in `PROJECT_ANALYSIS.md`).

---

## What Version 1.0 actually is

A multi-company (G-STONE GALLERY, KORONA PREMIUM, NEOLITH BAKU), trilingual (Azerbaijani default, Russian, English fallback) CRM with:
- Auth, RBAC (owner/manager/rep/viewer), full audit log, internal event bus
- A stone-industry Customer model (contact channels, company affiliation, 14-stage sales pipeline, free-text notes) and Lead capture across 9 channels
- A Dashboard with real pipeline counters
- Search, sort, inline quick-actions, keyboard shortcuts, and a global quick-create menu tuned for 8-hour daily use
- A documented, fixed set of known gaps (`RELEASE_CHECKLIST.md`) — Critical/High items are fixed; Medium/Low items are intentionally deferred, and several of them are exactly what 1.1 picks up

This document does not repeat that audit; it turns the deferred items (and obvious next product steps) into a sequenced plan.

---

## Version 1.1 — Finish what 1.0 started

**Theme:** close the gaps already identified during the Release Candidate and Business Optimization passes. No new entities, no new modules — these are completions and hardening of existing CRM features.

| Feature | Priority | Business value | Dependencies | Complexity |
|---|---|---|---|---|
| **Assigned Manager picker** — a real dropdown of company users on the customer form/profile, replacing the current free-typed UUID (which has no UI at all today) | High | Direct: managers can't currently be assigned through the UI despite the backend fully supporting and validating it — this is the single most visible gap between "built" and "usable" | Needs a new `GET` company-users list endpoint (small, additive) | S |
| **Save/action confirmation feedback** (toasts) for status changes, note saves, customer creation | High | Removes the "did that actually save?" doubt during fast, repeated daily use — directly named in `UI_UX_GUIDELINES.md` and never implemented | None | S |
| **"Load more" pagination UI** wired to the cursor API that already exists server-side | Medium | Prevents silent data loss once a company passes ~25–100 customers; the backend contract is already correct, only the UI never consumes it | None — backend done in `0f6eba6` | S |
| **Upload content-type allowlist** (images/PDF/office docs) | Medium | Security hardening flagged as Medium in `RELEASE_CHECKLIST.md` (M1); low urgency since uploads are never served as executable content today, but cheap to close before the upload feature sees real traffic | None | S |
| **Shareable/persisted list filters** (status, search, sort reflected in the URL) | Medium | A manager re-opening "my In Production customers" shouldn't have to re-filter every time; also makes filtered views bookmarkable/shareable between teammates | None | S |
| **Bulk actions on the Customer list** (multi-select archive, multi-select status change) | Medium | Saves real time when cleaning up stale inquiries in bulk, a recurring weekly task for a gallery manager | None | M |
| **Remove orphaned `customer.type` exposure** and reconcile the legacy `Contact` sub-entity with the stone-industry profile fields (M2/M8 in the checklist) | Low | Pure tech-debt cleanup; no user-facing value, but reduces confusion for future development | None | S |
| **Refresh-token revocation** (logout-everywhere, Redis-backed denylist) | Low | Security hardening (M7); low urgency for a 3-company internal tool, but Redis is already provisioned and unused | Redis wiring (infra already exists, just unused) | S |

**Suggested sequencing within 1.1:** Manager picker and toasts first (highest visible value, smallest effort), then pagination UI and filter persistence, then bulk actions, then the two cleanup/hardening items.

---

## Version 1.2 — Make the CRM the place reps actually live

**Theme:** the gap between "a CRM that stores records" and "a CRM that runs a sales rep's day." These are still CRM-only features (no new top-level module), but each is a meaningfully sized addition, not a polish item.

| Feature | Priority | Business value | Dependencies | Complexity |
|---|---|---|---|---|
| **Tasks & Reminders** (due-date follow-ups, assigned to a rep, surfaced on the Dashboard and as overdue alerts) | High | The single biggest missing daily-use loop: today nothing reminds a rep to call a customer back. This is the most-requested kind of feature in any CRM rollout | Manager picker (1.1, for assignment) | M |
| **Per-company configurable pipeline stages & lead sources** (today the 14 statuses and 9 channels are hardcoded platform-wide, even though the architecture and DB design always intended per-company configuration) | High | KORONA PREMIUM and NEOLITH BAKU may not want G-STONE GALLERY's exact stone-fabrication pipeline; this was a stated architectural goal not yet delivered | A minimal company-settings admin screen (doesn't exist yet) | M |
| **Role-scoped Dashboard & list views** ("my customers" vs. "all customers" depending on role) | Medium | Reps shouldn't have to filter out the whole company's pipeline to see their own work | Manager picker (1.1) | M |
| **Export Customers/Leads to CSV** | Medium | Standard expectation for any CRM; used for offline reporting, accounting handoff, marketing list pulls | None | S |
| **Email/notification delivery for Task reminders** (in-app today only; email or SMS next) | Medium | Extends Tasks & Reminders beyond "must be logged in to see it" | Tasks & Reminders (this version); an email provider integration | L |
| **Attachment previews/thumbnails** (images shown inline, not just a filename) | Low | Quality-of-life for the Attachments card, especially for site/product photos | None | M |
| **Mobile-responsive verification pass** (the frozen architecture is API-first/mobile-ready by design; this is validating that promise, not building a mobile app) | Low | De-risks an eventual native mobile client without committing to building one yet | None | S |

**Suggested sequencing within 1.2:** Tasks & Reminders first (it's the headline feature), then configurable pipeline/lead-source settings (it unblocks the other two companies from being properly served), then role-scoped views, then the smaller items.

---

## Version 2.0 — The first modules beyond CRM

**Theme:** per the frozen plugin architecture (`PROJECT_ANALYSIS.md` §9), CRM was always module one of ten. Version 2.0 is where the platform stops being "a CRM" and starts being "an ERP." **Approved architectural change:** a new **Stone Catalog** module is inserted before Sales — quotations cannot be real without real stone brands, collections, slabs, pricing, and technical specifications to quote *from*, so Sales now depends on the Catalog rather than going straight from CRM to Quotes.

**Revised dependency chain (approved):**

```
CRM
 ↓
Tasks & Reminders        (Version 1.2)
 ↓
Stone Catalog             (Version 2.0 — new, moved ahead of Sales)
 ↓
Sales (Quotes)
 ↓
Orders
 ↓
Production
 ↓
Installation
 ↓
Finance
 ↓
Reports
```

| Feature | Priority | Business value | Dependencies | Complexity |
|---|---|---|---|---|
| **Stone Catalog module** — brands, collections, slabs/lots, technical specifications (dimensions, finish, material type), and price lists | High | The foundational data Sales cannot function without: today there is no system of record for what G-STONE GALLERY, KORONA PREMIUM, and NEOLITH BAKU actually sell or at what price — every quote is currently built from memory or an external spreadsheet | CRM + Tasks & Reminders (1.2) | XL |
| **Sales module: Quotes** (line items drawn from the Catalog, pricing, linked to a Customer) | High | The direct next step after a customer reaches "Quote Sent" in the pipeline today — right now that status exists with nothing behind it, and a quote without real catalog items isn't a real quote | Stone Catalog | L |
| **Orders** (created from an accepted Quote, triggers the `OrderApproved` event already named in the architecture) | High | Closes the loop from "won deal" to an actual order record; `OrderApproved` is already a documented event other future modules (Production) will subscribe to | Sales (Quotes) | L |
| **Production module: work orders** (fabrication/cutting jobs linked to an Order, consuming specific slabs/lots from the Catalog) | High | Core stone-fabrication workflow; the "In Production" pipeline status already exists in CRM with nothing operational behind it yet — and now has real slab data to consume against, via the Catalog | Orders (+ reads from Stone Catalog for slab/lot consumption) | XL |
| **Installation module: scheduling & crew assignment** | Medium | Matches the "Installation Scheduled" / "Installed" statuses already live in the CRM pipeline today with no operational system behind them | Production | L |
| **Finance module: invoicing & payments** | High | Closes the revenue loop; "Payment Received" already exists as a CRM status with nothing behind it; invoice line items now trace back to real Catalog pricing | Orders + Installation completion events | L |
| **Reports module: cross-module dashboards** | Medium | Only becomes valuable once Catalog/Sales/Production have real data flowing | All of the above | M |

**Why Stone Catalog before Sales, specifically:** a quote is only as real as what's being quoted. Without brands, collections, slabs, technical specs, and pricing as actual data, "Sales" would mean typing arbitrary line-item text into a Quote — no different from a paper quote. The Catalog is now the dependency that makes every downstream module (Sales, Production, Finance) reference real, priced, trackable stone instead of free text. This also absorbs what earlier roadmap drafts called "Inventory" (slab/lot tracking) — in a stone-gallery business, the catalog *is* the inventory; modeling them as one module avoids duplicating slab/lot data across two places.

**Purchasing** (suppliers and purchase orders, used to restock the Catalog) remains on the longer-term module list but is not on this critical path — it depends on the Stone Catalog existing first and can be sequenced after Version 2.0 lands, once restocking becomes the active bottleneck rather than initial cataloging.

**Out of scope for this document:** Marketing and AI modules remain on the original ten-module list but are deliberately not sequenced into 1.1/1.2/2.0 — Marketing depends on Sales/CRM data maturity, and AI is explicitly designed to be the *last* module added (per `PROJECT_ANALYSIS.md` §9), once there's real document/image volume from Sales, the Stone Catalog, and Installation to act on.

---

## Complexity key

- **S** (Small): a few files, one focused PR, low risk
- **M** (Medium): a small feature slice, may touch backend + frontend, moderate testing surface
- **L** (Large): a real feature with its own data model additions, multiple screens, meaningful test coverage
- **XL** (Extra Large): a new module-sized effort — new domain model, new Clean Architecture layers, new migration set

---

## Summary

| Version | Theme | Net-new entities? | Net-new modules? |
|---|---|---|---|
| 1.1 | Finish & harden what 1.0 shipped | No | No |
| 1.2 | Make the CRM a daily operating tool | Tasks/Reminders only | No |
| 2.0 | First modules beyond CRM | Yes (Stone Catalog → Sales/Quotes → Orders → Production → Installation → Finance → Reports) | Yes |

## Change log

- **2026-06-30:** Approved with one architectural change — inserted **Stone Catalog** ahead of Sales in the Version 2.0 dependency chain, since quotations require real stone brands, collections, slabs, pricing, and technical specifications. The chain is now CRM → Tasks & Reminders → Stone Catalog → Sales (Quotes) → Orders → Production → Installation → Finance → Reports. The standalone "Inventory" module from the original draft is absorbed into Stone Catalog (slab/lot tracking belongs with the catalog data it describes); Purchasing remains a later, off-critical-path module.

Awaiting approval before any of this is built.
