# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

G-STONE ERP: a multi-company (G-STONE GALLERY, KORONA PREMIUM, NEOLITH BAKU), trilingual (Azerbaijani default, Russian, English fallback) ERP platform for a stone/slab gallery business. Built as a plugin-based core hosting independently installable business modules (CRM, Stone Catalog, Sales, Orders, Production, Installation, Finance, Reports, ...), each internally structured with Clean Architecture and integrated via an internal event bus.

The frozen design docs at the repo root are the source of truth for anything not obvious from the code itself — read them before making architectural changes, not just this file:
- `PROJECT_ANALYSIS.md` — business goals, full system/database/security/deployment architecture, the 10-module roadmap.
- `DATABASE_DESIGN.md` — ER diagram, tables, relationships, indexes, constraints.
- `API_SPECIFICATION.md` — REST endpoints, auth, schemas, versioning, error format.
- `UI_UX_GUIDELINES.md` — design system, color palette, typography, component/navigation rules.
- `ROADMAP.md` — what's delivered vs. planned, in priority order, with the module dependency chain and rationale for sequencing.

## Repository layout

- `backend/` — FastAPI + SQLAlchemy 2.0 + Alembic (Python).
- `frontend/` — Next.js 15 + TypeScript, screens for every backend module.

## Commands

### Backend (`backend/`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed.py          # seeds owner@g-erp.example / ChangeMe123! on all 3 companies
uvicorn main:app --reload       # serves http://localhost:8000, docs at /api/v1/docs
pytest                          # full suite
pytest tests/crm/test_customers_api.py            # one file
pytest tests/crm/test_customers_api.py::test_name # one test
pytest tests/test_core_independence.py            # the architecture guardrail alone
lint-imports                                       # import-linter: same core/module boundary, enforced in CI
```

After changing any module's SQLAlchemy models: `alembic revision --autogenerate -m "..."` then `alembic upgrade head` — but first make sure the module's `infrastructure/models` package is imported in `migrations/env.py`, or autogenerate won't see the new tables.

### Frontend (`frontend/`)

```bash
npm install
cp .env.example .env.local
npm run dev          # requires the backend running at NEXT_PUBLIC_API_BASE_URL (default localhost:8000)
npm run build
npm run lint
npm run typecheck    # tsc --noEmit
```

## Backend architecture

### Core vs. modules — the one rule that matters

The dependency direction is strictly **module → core, never core → module**. This is not just convention: `backend/tests/test_core_independence.py` is an executable guardrail that ASTs every file under `core/` and fails the build if any of them import from `modules.*` (the one intentional exception is `core/module_registry/registry.py`, which loads modules dynamically via `importlib` using plain strings). `pyproject.toml` also configures `import-linter` with the same forbidden-imports contract, run as `lint-imports`. Both checks — the full `pytest` suite and `lint-imports` — run automatically on every push/PR via `.github/workflows/ci.yml`, so a violation fails CI rather than depending on someone remembering to run either locally. Never make `core/` import from a module to "just this once" solve a problem — solve it via the event bus, the manifest contract, or a shared `core/` abstraction instead.

`core/` never imports a module's domain/application/infrastructure internals directly — the *only* thing it touches per module is a single `MODULE_MANIFEST` object (`core/module_registry/contracts.py`), which declares the module's router, permissions, navigation entries, settings schema, and event subscriptions. `core/module_registry/registry.py`'s `INSTALLED_MODULES` list is the entire "install a module" step — nothing else in `core/` changes when a module is added.

### Adding a new module

1. Create `modules/<name>/` following the `ModuleManifest` contract (`core/module_registry/contracts.py`) — use `modules/crm/` or `modules/catalog/` as reference implementations.
2. Add `"modules.<name>"` to `INSTALLED_MODULES` in `core/module_registry/registry.py`.
3. Import the module's `infrastructure/models` package in `migrations/env.py` so Alembic autogenerate sees its tables, and in `tests/conftest.py` so the in-memory test DB creates them.
4. Nothing else in `core/` changes.

### Module internal structure (Clean Architecture)

Every module follows `modules/<name>/{domain,application,infrastructure,presentation}`:
- `domain/` — entities, value objects, domain events, domain exceptions. No framework dependencies.
- `application/` — use cases, DTOs, and (for modules that react to other modules' events) `event_handlers/`.
- `infrastructure/` — SQLAlchemy `models/` and `repositories/` implementing domain-defined interfaces.
- `presentation/` — FastAPI `api/` routers and Pydantic `schemas/`, mounted by the core at `/api/v1/<module-name>/*`.
- `manifest.py`, `navigation.py`, `permissions.py`, `settings_schema.py` at the module's top level — the pieces assembled into that module's `MODULE_MANIFEST`.

### Cross-cutting concerns (every write action, every module)

Every write action must both record an append-only audit log entry (`core.audit_log`, via `core/audit/service.py`) and publish a domain event (`core.event_log`, via `core/events/event_bus.py`) — this is enforced by tests in every module (e.g. `tests/crm/test_audit_and_events.py`), not just done ad hoc. When adding a new write use case, follow the existing pattern in a sibling module rather than reinventing it.

Multi-tenancy: every tenant-owned table (core or module) carries a `company_id` (see `core/db/mixins.py`'s `CompanyScopedMixin` docstring — the FK/index is declared per-model since declarative mapping needs a resolvable target, but the pattern is mandatory). RBAC (`core/rbac/`) is permission-string based (e.g. `"crm:deals:write"`), enforced server-side via the `require_permission(...)` FastAPI dependency — never rely on the frontend hiding a button as the real control. `CurrentUser.active_company_id` scopes every request to one company at a time; `require_active_company` / `require_permission` both fail closed if no company is active.

Primary keys are UUIDs stored via the `GUID` `TypeDecorator` in `core/db/mixins.py` (native `UUID` on Postgres, `CHAR(36)` on SQLite) — this is what lets the test suite run entirely against in-memory SQLite while production runs Postgres/Supabase.

### Tests

`backend/tests/` mirrors `backend/modules/` (one directory per module, plus core-level tests at the top). `tests/conftest.py` builds a fresh in-memory SQLite DB per test via a fixture (`test_engine`/`db_session`), importing every installed module's models so `Base.metadata.create_all` sees all tables — a new module's models package must be added there too. The login rate limiter is a process-level singleton reset between tests by an autouse fixture; keep that pattern in mind if you add another such singleton.

## Frontend architecture

- Route groups: `app/(app)/` holds all authenticated screens (one subdirectory per module — `crm/`, `catalog/`, `sales/`, `orders/`, `production/`, `installation/`, `reports/`); `app/login/` is the one unauthenticated route.
- `lib/api/` — one file per backend module (`crm.ts`, `catalog.ts`, `sales.ts`, ...), each a thin typed wrapper around that module's REST endpoints. Add new backend calls here, not inline in components.
- `components/ui/` — shared design-system primitives (Button, Badge, Card, Field, EmptyState, StatCard, SortableHeader, Skeleton, charts). Reuse these rather than writing new ad hoc styled elements; colors/typography come directly from `UI_UX_GUIDELINES.md` and are expressed as `tailwind.config.ts` tokens.
- **i18n**: `next-intl`, but deliberately *not* using its URL-based routing (no `/az/...`, `/ru/...` segments — routes stay as `/login`, `/crm/customers`, etc.). Instead `lib/i18n/locale-context.tsx` provides a client-side `LocaleProvider` holding the active locale in React state, wrapping `NextIntlClientProvider`. Never hardcode UI strings — add keys to all three of `locales/az.json`, `locales/ru.json`, `locales/en.json` (`en` is the fallback for missing keys via `deepMerge` in `lib/i18n/config.ts`). The selected locale persists to `localStorage` (`g_erp_locale`), not the backend — there is no per-user locale field in the DB yet.
- Known limitation: a handful of strings (e.g. activity-timeline entries like "Customer 'X' created.") are generated server-side and stored as data, so they aren't covered by the frontend i18n pass and always render in English.

## Module delivery status

See `ROADMAP.md` for the authoritative, current status and the module dependency chain (`CRM → Tasks & Reminders → Stone Catalog → Sales → Orders → Production → Installation → Finance → Reports`). Check it and `git log` before assuming a module is or isn't built — this repo moves fast (several modules have landed within days of each other).
