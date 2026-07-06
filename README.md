# G-STONE ERP

Enterprise platform (ERP, CRM-first module) for:

- G-STONE GALLERY
- KORONA PREMIUM
- NEOLITH BAKU

Project started: 29.06.2026

## Architecture

The system is architected as a plugin-based core hosting independently installable business modules (CRM, Stone Catalog, Sales, Orders, Production, Installation, Finance, Communication Center, Reports — plus Marketing and AI, still unbuilt, from the original ten-module list), each internally structured with Clean Architecture and integrated via an internal event bus. Full design documents (frozen, updated in place as each module actually ships):

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

See [ROADMAP.md](ROADMAP.md) for the full delivery history and what's next (Marketing and AI remain unbuilt, per the original ten-module list).

## Repository layout

- [`backend/`](backend) — FastAPI + SQLAlchemy 2.0 + Alembic, Python. See [backend/README.md](backend/README.md) for setup, run, and test instructions.
- [`frontend/`](frontend) — Next.js 15 + TypeScript. See [frontend/README.md](frontend/README.md) for setup instructions.

## Stack

Frontend: Next.js 15, TypeScript. Backend: FastAPI, SQLAlchemy 2.0, Alembic. Database: PostgreSQL (Supabase). Cache: Redis. Background jobs: Celery + Redis. Storage: Supabase Storage.
