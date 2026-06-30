# G-STONE ERP

Enterprise platform (ERP, CRM-first module) for:

- G-STONE GALLERY
- KORONA PREMIUM
- NEOLITH BAKU

Project started: 29.06.2026

## Architecture

The system is architected as a plugin-based core hosting independently installable business modules (CRM, Sales, Inventory, Purchasing, Production, Installation, Finance, Reports, Marketing, AI), each internally structured with Clean Architecture and integrated via an internal event bus. Full design documents (frozen):

- [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) — business goals, requirements, full system/database/security/deployment architecture, module roadmap.
- [DATABASE_DESIGN.md](DATABASE_DESIGN.md) — ER diagram, tables, relationships, indexes, constraints.
- [API_SPECIFICATION.md](API_SPECIFICATION.md) — REST endpoints, auth, schemas, versioning, error format.
- [UI_UX_GUIDELINES.md](UI_UX_GUIDELINES.md) — design system, color palette, typography, component/navigation rules.

## Status

- **Phase 1 — Core Platform**: complete ([backend/](backend)).
- **Phase 2 — CRM module**: complete (backend + frontend screens).

## Repository layout

- [`backend/`](backend) — FastAPI + SQLAlchemy 2.0 + Alembic, Python. See [backend/README.md](backend/README.md) for setup, run, and test instructions.
- [`frontend/`](frontend) — Next.js 15 + TypeScript. See [frontend/README.md](frontend/README.md) for setup instructions.

## Stack

Frontend: Next.js 15, TypeScript. Backend: FastAPI, SQLAlchemy 2.0, Alembic. Database: PostgreSQL (Supabase). Cache: Redis. Background jobs: Celery + Redis. Storage: Supabase Storage.
