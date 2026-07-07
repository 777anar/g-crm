# Changelog

All notable changes to this project are documented in this file. See [ROADMAP.md](ROADMAP.md) for full delivery narratives, rationale, and what's next; this file is the terse, dated summary.

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
