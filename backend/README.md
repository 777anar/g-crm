# G-STONE ERP Backend

FastAPI plugin core + business modules, built per the frozen architecture in [`PROJECT_ANALYSIS.md`](../PROJECT_ANALYSIS.md), [`DATABASE_DESIGN.md`](../DATABASE_DESIGN.md), and [`API_SPECIFICATION.md`](../API_SPECIFICATION.md).

## Status

- **Phase 1 / Step 1 — Core Platform**: complete. Auth, RBAC, audit logging, the event bus, storage, and the module registry — proven to boot and serve real endpoints with zero business modules installed.
- **Phase 2 — CRM module**: complete. The first production business module, built as a real plugin (Clean Architecture: Domain → Application → Infrastructure → Presentation), with zero changes required to any core file.
- **Version 2.0 — Stone Catalog module**: complete. The second business module — Brand, Collection, Stone Material, Slab, Warehouse, Price List, and material images/documents — built ahead of Sales per [`ROADMAP.md`](../ROADMAP.md)'s dependency chain, since quotations need real stone data to quote from.

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

167 tests, all passing: core (boot-standalone, RBAC rules, event bus, import-boundary), CRM (domain entities, every API endpoint, RBAC enforcement, multi-company isolation, and — for every write action — that it produced both an audit log entry and a domain event), and Stone Catalog (full CRUD per entity, brand/collection-mismatch validation, duplicate-slab-number conflict, the full slab status transition graph including rejected illegal transitions, price-list upsert idempotency, image/document linking via the shared documents endpoint, and multi-company isolation).

Includes an executable architecture guardrail (`tests/test_core_independence.py`) that fails the build if any `core/` file imports from `modules.*`.

## CRM Module (Phase 2)

Mounted at `/api/v1/crm/*`. Implements:

- **Customer management**: create, edit, archive (soft delete), profile, notes, attachments.
- **Lead management**: Instagram, Facebook, Messenger, WhatsApp (channel ready; no inbound webhook integration yet), and Manual capture — all through one `source_channel`-driven endpoint, plus lead-to-customer conversion.
- **Customer profile**: contact info, company, assigned manager, lead source, advertising campaign, activity timeline, notes, attachments, and Projects/Quotes/Orders/Payments sections (intentionally empty — owned by the Production, Sales, and Finance modules, not yet installed).
- **Every write action** records an append-only audit log entry (`core.audit_log`) and publishes a domain event (`core.event_log`): `CustomerCreated`, `CustomerUpdated`, `CustomerArchived`, `CustomerNoteAdded`, `LeadCreated`, `LeadConverted`.

Module layout: `modules/crm/{domain,application,infrastructure,presentation}` — see `modules/crm/manifest.py` for the plugin registration (permissions, navigation, settings schema, event subscriptions).

## Stone Catalog Module (Version 2.0)

Mounted at `/api/v1/catalog/*`. Implements:

- **Brand / Collection / Stone Material**: the product hierarchy (e.g. NEOLITH → a collection → "Calacatta Gold" with material type, color, finish, thickness, dimensions, country of origin).
- **Slab**: individually tracked physical inventory with a unique slab number per company, lot number, barcode, warehouse + rack location, exact dimensions, an application-computed area in m², weight, and a 5-state lifecycle (`available`/`reserved`/`sold`/`in_production`/`scrap`) enforced by a domain-layer transition graph — `sold` and `scrap` are terminal.
- **Warehouse**: multiple physical storage locations per company.
- **Price List / Price List Entry**: named, company-specific price lists with cost/sale pricing per material (upsert semantics — re-submitting a material updates its entry rather than erroring).
- **Material Image / Material Document**: thin links from a Material to an already-uploaded core `Document` (gallery/thumbnail/bookmatch images; technical PDF/installation guide/cleaning guide) — reuses the existing storage pipeline rather than reimplementing file handling.
- **Every write action** records an audit log entry and publishes a domain event: `BrandCreated`, `CollectionCreated`, `MaterialCreated`, `MaterialUpdated`, `WarehouseCreated`, `SlabCreated`, `SlabStatusChanged`, `PriceListCreated`, `PriceListEntryUpserted`.

Module layout: `modules/catalog/{domain,application,infrastructure,presentation}` — see `modules/catalog/manifest.py` for the plugin registration.

## Adding a module

1. Create `modules/<name>/` following the contract in `core/module_registry/contracts.py` (see `modules/crm/` for a complete reference implementation).
2. Add `"modules.<name>"` to `INSTALLED_MODULES` in `core/module_registry/registry.py`.
3. Import the module's `infrastructure/models` package in `migrations/env.py` so Alembic autogenerate sees its tables.
4. Nothing else in `core/` changes.
