# Changelog

All notable changes to this project are documented in this file. See [ROADMAP.md](ROADMAP.md) for full delivery narratives, rationale, and what's next; this file is the terse, dated summary.

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
