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

## Status

- **Phase 1 — Core Platform**: complete ([backend/](backend)) — auth, RBAC, audit log, event bus, storage, module registry.
- **Phase 2 — CRM module**: complete, including Tasks & Reminders (Version 1.2).
- **Version 2.0–2.6 — ERP module chain**: complete — Stone Catalog, Sales (Quotes), Orders, Production (work orders), Installation (scheduling/crews), Finance (invoicing/payments), and Reports (cross-module dashboards).
- **Version 2.7 — Communication Center**: complete — a unified omnichannel inbox (WhatsApp Business, Instagram Direct, Facebook Messenger, Email, SMS) integrated with CRM, with a provider abstraction layer standing in for real channel integrations (none are wired up yet, by design).
- **Version 2.8 — AI Sales Assistant**: complete — provider-agnostic AI recommendations (lead scoring, conversation intelligence, quote intelligence, task suggestions) across CRM, Communication, Sales, and Tasks, with a dedicated AI Dashboard. Every recommendation requires an explicit human Accept/Reject/Edit; no real LLM provider is wired up yet, by design. This closes out the original ten-module list, save Marketing.
- **Version 2.8.1 — UX & Platform Polish**: complete — a frontend-only pass across all modules: a real design-system token layer (Montserrat font, CSS-variable-based colors) with dark mode, an improved table toolkit (column resize/visibility, sticky headers, saved filters) on the busiest list pages, better form loading/validation/success feedback, a mobile slide-over navigation drawer, accessibility baseline (focus-visible, skip link), and print-friendly layouts. No backend files changed and no API contracts changed.
- **Version 2.9 — Real Integrations**: complete — real WhatsApp Business Cloud API, Instagram Messaging API, Messenger Send API, SMTP+IMAP email, and Twilio SMS providers for the Communication Center, plus a generic webhook provider for arbitrary partner systems. Encrypted per-channel credentials, connection testing, health monitoring, signature-verified inbound webhooks, delivery/read status sync, a retry queue for failed sends, and a Provider Diagnostics/Webhook Monitor admin page. The `ChannelProvider` interface is unchanged; a channel with no credential configured still uses `NullChannelProvider` exactly as before.
- **Version 2.9.1 — Enterprise Polish**: complete — a production-readiness audit across all ten shipped modules (no new features, no business-logic or API changes): application-level logging added to previously-silent error paths, an N+1 query fix in Sales quote acceptance, a real silent-failure bug fixed on several detail pages (write actions with no error feedback at all), duplicated table-wrapper styling consolidated across 8 list pages, and a hardened production-boot guard for the channel-credentials encryption key. See [CHANGELOG.md](CHANGELOG.md) for the full list.

See [ROADMAP.md](ROADMAP.md) for the full delivery history and what's next (Marketing remains unbuilt, per the original ten-module list).

## Repository layout

- [`backend/`](backend) — FastAPI + SQLAlchemy 2.0 + Alembic, Python. See [backend/README.md](backend/README.md) for setup, run, and test instructions.
- [`frontend/`](frontend) — Next.js 15 + TypeScript. See [frontend/README.md](frontend/README.md) for setup instructions.

## Stack

Frontend: Next.js 15, TypeScript. Backend: FastAPI, SQLAlchemy 2.0, Alembic. Database: PostgreSQL (Supabase). Cache: Redis. Background jobs: Celery + Redis. Storage: Supabase Storage.
