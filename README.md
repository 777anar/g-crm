# G-STONE ERP

Enterprise platform (ERP, CRM-first module) for:

- G-STONE GALLERY
- KORONA PREMIUM
- NEOLITH BAKU

Project started: 29.06.2026

## Architecture

The system is architected as a plugin-based core hosting independently installable business modules (CRM, Stone Catalog, Sales, Orders, Production, Installation, Finance, Communication Center, Reports, AI Sales Assistant — plus Marketing, still unbuilt, from the original ten-module list), each internally structured with Clean Architecture and integrated via an internal event bus. Full design documents (frozen, updated in place as each module actually ships):

- [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) — business goals, requirements, full system/database/security/deployment architecture, module roadmap.
- [DATABASE_DESIGN.md](DATABASE_DESIGN.md) — ER diagram, tables, relationships, indexes, constraints.
- [API_SPECIFICATION.md](API_SPECIFICATION.md) — REST endpoints, auth, schemas, versioning, error format.
- [UI_UX_GUIDELINES.md](UI_UX_GUIDELINES.md) — design system, color palette, typography, component/navigation rules.
- [ROADMAP.md](ROADMAP.md) — delivery status and dependency chain for every module, kept current as each one ships.
- [PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) — the Phase 3 application-wide audit ahead of real daily use by G-STONE GALLERY: findings, fixes, and what was deliberately deferred.

## Status

- **Phase 1 — Core Platform**: complete ([backend/](backend)) — auth, RBAC, audit log, event bus, storage, module registry.
- **Phase 2 — CRM module**: complete, including Tasks & Reminders (Version 1.2).
- **Version 2.0–2.6 — ERP module chain**: complete — Stone Catalog, Sales (Quotes), Orders, Production (work orders), Installation (scheduling/crews), Finance (invoicing/payments), and Reports (cross-module dashboards).
- **Version 2.7 — Communication Center**: complete — a unified omnichannel inbox (WhatsApp Business, Instagram Direct, Facebook Messenger, Email, SMS) integrated with CRM, with a provider abstraction layer standing in for real channel integrations (none are wired up yet, by design).
- **Version 2.8 — AI Sales Assistant**: complete — provider-agnostic AI recommendations (lead scoring, conversation intelligence, quote intelligence, task suggestions) across CRM, Communication, Sales, and Tasks, with a dedicated AI Dashboard. Every recommendation requires an explicit human Accept/Reject/Edit; no real LLM provider is wired up yet, by design. This closes out the original ten-module list, save Marketing.
- **Version 2.8.1 — UX & Platform Polish**: complete — a frontend-only pass across all modules: a real design-system token layer (Montserrat font, CSS-variable-based colors) with dark mode, an improved table toolkit (column resize/visibility, sticky headers, saved filters) on the busiest list pages, better form loading/validation/success feedback, a mobile slide-over navigation drawer, accessibility baseline (focus-visible, skip link), and print-friendly layouts. No backend files changed and no API contracts changed.
- **Version 2.9 — Real Integrations**: complete — real WhatsApp Business Cloud API, Instagram Messaging API, Messenger Send API, SMTP+IMAP email, and Twilio SMS providers for the Communication Center, plus a generic webhook provider for arbitrary partner systems. Encrypted per-channel credentials, connection testing, health monitoring, signature-verified inbound webhooks, delivery/read status sync, a retry queue for failed sends, and a Provider Diagnostics/Webhook Monitor admin page. The `ChannelProvider` interface is unchanged; a channel with no credential configured still uses `NullChannelProvider` exactly as before.
- **Version 2.9.1 — Enterprise Polish**: complete — a production-readiness audit across all ten shipped modules (no new features, no business-logic or API changes): application-level logging added to previously-silent error paths, an N+1 query fix in Sales quote acceptance, a real silent-failure bug fixed on several detail pages (write actions with no error feedback at all), duplicated table-wrapper styling consolidated across 8 list pages, and a hardened production-boot guard for the channel-credentials encryption key. See [CHANGELOG.md](CHANGELOG.md) for the full list.
- **Version 2.9.2 — Production Readiness & G-STONE Onboarding ("Phase 3")**: complete — an application-perspective audit ahead of real daily use by G-STONE GALLERY (navigation, branding, every CRUD flow, filters/sort/export, permissions, company switching, i18n, dev artifacts), driven live against the running app rather than source review alone. Found and fixed one release-blocking bug (Sales Projects' "Create Project" customer picker 400'd on every load), an orders sort parameter that was silently ignored, a missing Sales Quote settings-edit UI, missing Catalog Brand/Warehouse archive/restore controls, a missing favicon, and static-only browser tab titles. See [PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) for the full findings, fixes, and what was deliberately deferred.
- **Version 2.9.3 — Production Readiness follow-up**: complete — closed out the remaining Phase 3 findings: an untranslated Azerbaijani string, chart colors hardcoded to light mode (nearly invisible in dark mode), and a shared `Breadcrumb` component applied to the nine detail pages that previously used a plain "← Back to X" link instead. A finding from an earlier pass (a missing Customer "Restore" button) was investigated and found to require new backend logic that doesn't exist yet — recorded as an open gap rather than built. See [CHANGELOG.md](CHANGELOG.md) for the full list.
- **Version 2.10.0 — G-STONE Sprint 2 (Simplified Navigation & Layihə-Centric Workflow)**: complete — a frontend-led usability pass driven by real G-STONE office feedback ("this looks like an accounting system, not a gallery tool"). The primary sidebar was cut from ~20 flat entries to 9 module-level sections (İdarə Paneli, Müştərilər, Layihələr, Materiallar, İstehsal, Quraşdırma, Mesajlar, Hesabatlar, Ayarlar) with in-page secondary tabs for everything that used to have its own top-level entry; back-office pages that belong to 1C (Warehouses, Slabs, Price Lists, Invoices, Expenses) and messaging admin (Channels, Templates, Integrations) moved into a new `/settings` hub instead of being deleted. Seven new project-item ("piece") types — kitchen countertop, island, TV panel, bathroom furniture, flooring, stairs, table — were added to the Sales module's item-type vocabulary alongside the existing wall-cladding/vanity/backsplash types, each carrying its own material, production status, and installation status, matching how a stone gallery actually thinks about a project (a set of physical pieces, not abstract line items). The Material creation form now guides Brand → Stone name → Thickness → Size as a structured cascade (curated dropdown + manual "Other" override) instead of free-text thickness/dimensions fields, in preparation for a future supplier-catalog import. No backend schema changes and no data deleted — every moved page is still reachable at its existing URL. See [CHANGELOG.md](CHANGELOG.md) for the full list.

See [ROADMAP.md](ROADMAP.md) for the full delivery history and what's next (Marketing remains unbuilt, per the original ten-module list).

## Repository layout

- [`backend/`](backend) — FastAPI + SQLAlchemy 2.0 + Alembic, Python. See [backend/README.md](backend/README.md) for setup, run, and test instructions.
- [`frontend/`](frontend) — Next.js 15 + TypeScript. See [frontend/README.md](frontend/README.md) for setup instructions.

## Stack

Frontend: Next.js 15, TypeScript. Backend: FastAPI, SQLAlchemy 2.0, Alembic. Database: PostgreSQL (Supabase). Cache: Redis. Background jobs: Celery + Redis. Storage: Supabase Storage.
