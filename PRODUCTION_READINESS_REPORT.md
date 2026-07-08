# G-STONE ERP — Production Readiness Report

_Date: 2026-07-08_
_Phase: 3 — Production Readiness & G-STONE Onboarding_
_Scope: application-wide audit ahead of real daily use by G-STONE GALLERY. No new modules, no new features, no business-logic changes — fixes only for real issues found during this audit._

## Verdict

**The system is production-ready for G-STONE GALLERY's internal daily use.** One release-blocking bug (a broken Create flow) and several real usability/consistency gaps were found and fixed. A short list of lower-severity, larger-scoped items was found and deliberately deferred rather than rushed — see [Findings deferred](#findings-deferred-not-fixed) below, each with the reasoning.

## Method

Four independent research passes covered the application from different angles, followed by hands-on fixing and a live end-to-end smoke test:

1. **Backend audit** — demo/placeholder data, hardcoded secrets, TODO/debug artifacts, fake/mocked endpoints outside the two documented placeholders (Communication's `NullChannelProvider`, AI's `MockAIProvider`), missing RBAC checks on write endpoints, company-scoping gaps in repositories.
2. **Frontend branding/demo-data audit** — placeholder branding, hardcoded demo data, console/debug leftovers, dead mock arrays.
3. **Navigation/i18n/UX-states audit** — nav completeness, page titles, breadcrumbs, icons, EN/AZ/RU key parity and hardcoded strings, loading/empty/error state coverage.
4. **CRUD/filters/permissions/company-switch audit** — Create/Edit/Delete/Archive/Restore completeness per module, search/filter/sort/pagination/export, frontend permission gating, company-switch correctness.

Then: fixes applied directly against the codebase, `pytest` (backend), `tsc --noEmit` and `next build` (frontend), and a live Playwright smoke test against the real dev database and both running servers — login, company selection, every touched page, and hands-on exercise of each new/changed feature (brand archive/restore toggle, quote settings edit + reload persistence).

## Findings fixed

| # | Finding | Severity | Fix |
|---|---|---|---|
| 1 | Sales → Projects "Create Project" form's customer picker called `listCustomers({ limit: 200 })`, but the backend caps `limit` at 100 — every load 400'd and the dropdown silently rendered empty, **making Create unusable from that form.** | **Release-blocking** | Capped the request at 100 (`frontend/app/(app)/sales/projects/page.tsx`). |
| 2 | Orders list `sort` parameter was accepted end-to-end (API, frontend wrapper) but silently ignored — `OrderRepository.list()` always sorted by `created_at desc` regardless of its value. | High (dead API contract) | Wired a real `_SORTABLE` field map into `OrderRepository.list()`, matching the existing `ProjectRepository` pattern. Orders list now has working sortable column headers. |
| 3 | Sales Quotes had no way to edit VAT rate, discount, currency, validity date, or notes after creation — the backend `PATCH /quotes/{id}` endpoint and its translation keys already existed (from an earlier, unfinished pass) but nothing in the UI called it. | High (CRUD "Edit" gap on a core daily workflow) | Added an editable "Quote Settings" panel to the quote builder page, active while a quote is `draft`. |
| 4 | Frontend `Quote.discount_type` TypeScript type declared `"percentage"`; the backend only recognizes `"percent"` (`totals.py`). Dormant only because no UI ever set the field — would have silently zeroed every percentage discount the moment a real UI started sending it. | Latent correctness bug | Fixed the type; the new settings panel's dropdown sends the correct value. |
| 5 | Catalog Brands and Warehouses had no archive/restore affordance in the UI, despite the backend fully supporting an active/hidden status toggle (Materials already used the same capability). | Medium (CRUD "Archive/Restore" gap) | Added an Active/Hidden toggle button per row on both list pages; both lists now include hidden entities so a restore path exists. |
| 6 | No favicon — browser tabs showed a generic/blank icon. | Medium (branding, directly user-visible) | Added `frontend/app/icon.svg`, a "G" monogram in the app's primary brand color. |
| 7 | Every route showed the identical static "G-STONE ERP" browser tab title — no per-page differentiation. | Medium (navigation/UX) | `AppShell` now sets `document.title` to the active section's translated nav label on every in-app navigation. **Known remaining limitation**: a hard reload or a directly opened/bookmarked URL still shows the static title until the next in-app navigation, since the whole `(app)` route group is client-rendered behind a token-check gate and has no per-route `generateMetadata`. Fixing that fully would mean restructuring every route to a server-component wrapper — judged out of scope for an audit-only pass; documented here as a follow-up. |
| 8 | Sales Projects list had no status filter and no sortable columns, unlike every sibling list page — the backend already supported both. | Low/Medium (consistency) | Wired the existing `status`/`sort` backend params into the frontend. |
| 9 | Two dead, unused translation keys (`sales.serviceSettings` / `sales.servicePriceUpdated`) left over from an earlier abandoned feature, present in all three locale files with zero call sites. | Low (dev-artifact cleanup) | Removed; the freed slots hold the new Quote Settings translation keys instead, keeping all three locale files in parity. |

## Findings deferred (not fixed)

Each of these was considered and intentionally left alone, consistent with this pass's "no new features, no business-logic changes" mandate. They're recorded here so they aren't rediscovered as if new.

- **No icon library in the sidebar navigation.** `UI_UX_GUIDELINES.md` calls for one consistent icon set across all 21 nav items; the sidebar is currently text-only labels with no icon dependency in the project at all. Adding one is a real design-system decision (icon set choice, sizing, every nav entry touched) — a deliberate scope call, not an oversight, so it wasn't rushed into this pass.
- **No tablet-width (768–1023px) icon-only collapsed sidebar.** The guidelines specify this intermediate state; today tablet widths get the same mobile slide-over drawer as phones. Same reasoning as above — a real design addition, not a bug fix.
- **No client-side pagination UI on Customers/Leads/Orders/Production/Invoices/Slabs**, despite the backend's cursor-based API already supporting it. This is the same "Load more pagination UI" item already named and deferred in `ROADMAP.md`'s Version 1.1 section — re-confirmed still open during this audit, not a new regression. Real data volume at a single gallery business is unlikely to make this an active problem on day one, but it's the next thing to pick up once it does.
- **No frontend permission-gating of write buttons by role.** A viewer-role user currently sees the same Create/Edit/Archive buttons as an owner and would get a real `403` on submit rather than a disabled or hidden control. The backend's `require_permission(...)` dependency is the actual, authoritative security control here (per this repo's architecture) — this is a UX polish gap, not a security hole, and building a `usePermission()` hook plus gating it across the whole app is feature-sized work, not a fix.
- **Backend validation-error messages aren't localized.** When `ApiRequestError.message` carries a real backend error, it bypasses the frontend's `t()` translation fallback and shows raw English to AZ/RU users. Fixing this properly means the backend returning error *codes* the frontend maps to translated strings, a cross-cutting API contract change — out of scope here.
- **Production and Finance Invoices list pages have no backend `sort` parameter at all** (unlike Orders and Sales Projects, which already had one, just unwired on the frontend). Adding one means extending those two APIs, which this pass treated as feature work rather than a wiring fix.
- **Sales Quote Sections/Measurements support delete-and-recreate only, not in-place edit.** A real gap, but a working (if clunky) path exists today, and it's lower-traffic than the quote-level settings gap that was fixed. Left for a future pass.
- Pre-existing, already-documented gap (`ROADMAP.md` Version 2.9.1): only the Customers detail page has real breadcrumbs; every other detail page uses a "← Back to X" link instead. Reconfirmed still the state; not re-litigated here.

## Clean audit areas (no findings)

- **Backend**: no TODO/FIXME/debug `print()`/`NotImplementedError` outside expected locations (seed script, abstract provider base classes); no hardcoded secrets outside the boot-guarded dev defaults (`core/bootstrap/app_factory.py` already refuses to start with either placeholder secret outside development); no demo/placeholder business data in application code; every write endpoint checked carries `require_permission(...)` except the three signature-verified inbound webhook receivers (correctly public by design); every `get_by_id`/`get`/`find_by_id` repository method checked filters by `company_id`.
- **Frontend branding**: real "G-STONE ERP" branding and all three real company names throughout; no leftover Next.js boilerplate, "Acme", or Lorem ipsum; no mock arrays standing in for real API data on Dashboard, Reports, or the AI Dashboard; `package.json` name is reasonable, not a generic scaffold name.
- **i18n key parity**: `en.json`/`az.json`/`ru.json` are in exact sync (1,011 keys each before this pass's additions, all three still in parity after).
- **Loading/empty/error states**: every list page spot-checked (10 across CRM, Catalog, Sales, Orders, Production, Installation, Finance, Communication, AI) consistently implements a loading skeleton, an `EmptyState`, and visible error feedback — no silent-blank-page cases found.
- **Company switching**: works correctly via a deliberate full page reload after `selectCompany()` (documented in the component itself), which sidesteps any client-side cache staleness since no SWR/React Query/Redux layer exists to invalidate.

## Verification

- **Backend**: `pytest` — 492/492 passing.
- **Frontend**: `tsc --noEmit` — clean. `next build` — clean, all 41 routes.
- **Live smoke test** (Playwright against the real dev database and both running servers): login → company selection → Dashboard; Sales Projects, Orders, Catalog Brands/Warehouses list pages loaded with zero console/HTTP errors; a real brand created and its Active/Hidden toggle exercised end-to-end; a real project created, a quote created from it, its new Quote Settings panel edited (currency → USD) and confirmed persisted after a full page reload; favicon confirmed served at `/icon.svg`; in-app navigation confirmed to update the browser tab title correctly.

## Files changed

```
backend/modules/orders/infrastructure/repositories/order_repository.py
frontend/app/(app)/catalog/brands/page.tsx
frontend/app/(app)/catalog/warehouses/page.tsx
frontend/app/(app)/orders/page.tsx
frontend/app/(app)/sales/projects/page.tsx
frontend/app/(app)/sales/projects/[id]/quotes/[quoteId]/page.tsx
frontend/app/icon.svg (new)
frontend/components/app-shell.tsx
frontend/lib/types.ts
frontend/locales/az.json
frontend/locales/en.json
frontend/locales/ru.json
```
