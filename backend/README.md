# G-STONE ERP Backend

FastAPI plugin core + business modules, built per the frozen architecture in [`PROJECT_ANALYSIS.md`](../PROJECT_ANALYSIS.md), [`DATABASE_DESIGN.md`](../DATABASE_DESIGN.md), and [`API_SPECIFICATION.md`](../API_SPECIFICATION.md).

## Status

- **Phase 1 / Step 1 — Core Platform**: complete. Auth, RBAC, audit logging, the event bus, storage, and the module registry — proven to boot and serve real endpoints with zero business modules installed.
- **Phase 2 — CRM module**: complete. The first production business module, built as a real plugin (Clean Architecture: Domain → Application → Infrastructure → Presentation), with zero changes required to any core file.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed.py
```

## Run

```bash
uvicorn main:app --reload
```

API docs: http://localhost:8000/api/v1/docs

Seeded login: `owner@g-erp.example` / `ChangeMe123!` (owner role on all three companies: G-STONE GALLERY, KORONA PREMIUM, NEOLITH BAKU).

## Test

```bash
pytest
```

51 tests, all passing: core (boot-standalone, RBAC rules, event bus, import-boundary), and CRM (domain entities, every API endpoint, RBAC enforcement, multi-company isolation, and — for every write action — that it produced both an audit log entry and a domain event).

Includes an executable architecture guardrail (`tests/test_core_independence.py`) that fails the build if any `core/` file imports from `modules.*`.

## CRM Module (Phase 2)

Mounted at `/api/v1/crm/*`. Implements:

- **Customer management**: create, edit, archive (soft delete), profile, notes, attachments.
- **Lead management**: Instagram, Facebook, Messenger, WhatsApp (channel ready; no inbound webhook integration yet), and Manual capture — all through one `source_channel`-driven endpoint, plus lead-to-customer conversion.
- **Customer profile**: contact info, company, assigned manager, lead source, advertising campaign, activity timeline, notes, attachments, and Projects/Quotes/Orders/Payments sections (intentionally empty — owned by the Production, Sales, and Finance modules, not yet installed).
- **Every write action** records an append-only audit log entry (`core.audit_log`) and publishes a domain event (`core.event_log`): `CustomerCreated`, `CustomerUpdated`, `CustomerArchived`, `CustomerNoteAdded`, `LeadCreated`, `LeadConverted`.

Module layout: `modules/crm/{domain,application,infrastructure,presentation}` — see `modules/crm/manifest.py` for the plugin registration (permissions, navigation, settings schema, event subscriptions).

## Adding a module

1. Create `modules/<name>/` following the contract in `core/module_registry/contracts.py` (see `modules/crm/` for a complete reference implementation).
2. Add `"modules.<name>"` to `INSTALLED_MODULES` in `core/module_registry/registry.py`.
3. Import the module's `infrastructure/models` package in `migrations/env.py` so Alembic autogenerate sees its tables.
4. Nothing else in `core/` changes.
