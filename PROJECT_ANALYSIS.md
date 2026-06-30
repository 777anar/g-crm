# G-ERP — Enterprise Platform Analysis & Architecture

_Date: 2026-06-29_
_Status: **FROZEN.** Architecture approved 2026-06-29. This document is no longer subject to redesign except in response to a critical issue discovered during implementation (e.g., a security flaw, a structural flaw that blocks Phase 1, or a fundamental misunderstanding of requirements). Any such exception must be logged as an addendum to this file with rationale, not a silent rewrite. Detailed design now continues in [DATABASE_DESIGN.md](DATABASE_DESIGN.md), [API_SPECIFICATION.md](API_SPECIFICATION.md), and [UI_UX_GUIDELINES.md](UI_UX_GUIDELINES.md). Phase 1 implementation begins after those three documents are complete._

This revision finalizes the platform architecture before development begins. It supersedes revision 2 by upgrading the system from "modular by folder structure" to a true **plugin architecture with Clean Architecture layering and Event-Driven Architecture (EDA)**. The business goals, functional/non-functional requirements, stack, multi-company strategy, and module list from revision 2 remain unchanged and are restated briefly; the architectural sections (4, 5, 7, 8) are substantially rewritten.

---

## 1. Business Goals

- Run the full operational lifecycle of three companies — **G-STONE GALLERY**, **KORONA PREMIUM**, **NEOLITH BAKU** — in one platform: lead → sale → purchasing/inventory → production/fabrication → installation → invoicing/finance, wrapped by CRM and Marketing.
- Each company keeps its own data and configuration; ownership gets cross-company visibility.
- AI/automation (document analysis, image processing, future ML) is a first-class, long-term capability, not a bolt-on — this is why the backend stays in Python.
- New modules — including modules not yet named — must be **installable without modifying the core**, and the core must be able to run with zero business modules installed at all.
- The platform must serve **web and mobile clients identically**, through the same API surface.

## 2. Functional Requirements (summary, unchanged from revision 2)

Core modules: **CRM, Sales, Inventory, Purchasing, Production, Installation, Finance, Reports, Marketing, AI**. Each module's functional scope (contacts/leads/deals, quotes/orders, stock/lots, suppliers/POs, work orders, installation jobs, invoicing/payments, dashboards, campaigns, document/image AI) is as detailed in revision 2 and is not repeated here — this revision concerns *how* those modules are built and wired together, not *what* they do.

## 3. Non-Functional Requirements (carried forward, with additions)

All non-functional requirements from revision 2 (data isolation, performance, scalability, security, auditability, maintainability, localization, backups) remain in force. This revision adds:

| Category | Requirement |
|---|---|
| **Core independence** | The core platform must build, start, and run with zero business modules present. No core file may `import` from any module. |
| **Module self-containment** | A module must be addable or removable by adding/removing its directory and a registry entry — no edits to core files, no edits to other modules. |
| **Loose coupling via events** | Modules must not call each other directly in-process for cross-cutting business reactions (e.g., Production reacting to a sales order). They communicate by publishing/subscribing to domain events. |
| **API parity for all clients** | Every capability exposed to the web frontend must be reachable through the same versioned REST API used by the future mobile app — no web-only backend shortcuts (e.g., server-rendered-only logic, session-cookie-only auth) that a mobile client couldn't use. |
| **Testability per layer** | Domain logic must be testable without a database, HTTP framework, or external service — a direct consequence of Clean Architecture layering. |

## 4. Complete System Architecture

### 4.1 Confirmed Stack (unchanged)

| Layer | Technology |
|---|---|
| Frontend (web) | **Next.js 15** + **TypeScript** |
| Frontend (mobile) | Future native/cross-platform app (React Native or similar — decided later), consuming the same REST API |
| Backend | **FastAPI** (Python) |
| ORM | **SQLAlchemy 2.0** |
| Migrations | **Alembic** |
| Database | **PostgreSQL via Supabase** |
| Cache | **Redis** |
| Background jobs | **Celery + Redis** |
| File/object storage | **Supabase Storage** |
| Event transport (internal) | In-process event bus (Phase 1+), upgradeable to Redis Pub/Sub or a durable broker later if cross-process/cross-service event delivery is needed |

### 4.2 Architectural Style: Plugin Core + Clean Architecture per Module + Event-Driven Integration

Three architectural patterns combine here, each solving a different problem:

1. **Plugin architecture** — solves "how do modules get added/removed without touching the core." The core is a thin host; modules are self-contained plugins it discovers and mounts.
2. **Clean Architecture** — solves "how does each module stay maintainable and testable internally." Every module is internally layered: Domain → Application → Infrastructure → Presentation.
3. **Event-Driven Architecture** — solves "how do modules react to each other's business outcomes without depending on each other's code." Modules publish domain events; other modules (including the future AI module) subscribe.

These are complementary, not competing: plugin architecture defines module *boundaries*, Clean Architecture defines what's *inside* each boundary, and EDA defines how boundaries *communicate*.

### 4.3 The Core (Platform Host)

The core contains **only** generic, business-agnostic platform capabilities. It has zero knowledge of CRM, Sales, Inventory, or any other business concept.

```
core/
  bootstrap/
    app_factory.py          # builds the FastAPI app, mounts modules discovered by the registry
  module_registry/
    contracts.py            # ModuleManifest, ModulePlugin protocol/interface (the contract)
    registry.py             # discovers installed modules, validates manifests, mounts them
  auth/                      # authentication primitives (no business roles, just identity)
  rbac/                      # generic permission engine: modules REGISTER permissions, core ENFORCES them
  audit/                     # generic audit log writer (module-agnostic: module name is just a string field)
  storage/                   # Supabase Storage client wrapper, generic file API
  events/
    event_bus.py             # publish/subscribe primitives (the EDA backbone)
    event_envelope.py        # generic Event base type (id, name, company_id, payload, occurred_at)
  db/
    session.py               # SQLAlchemy session/engine management
    base.py                  # declarative base ONLY — no business models
  companies/
    # the one "module-like" exception: company/tenant registry is core, not a business module,
    # because every module depends on knowing what a company is. Treated as part of the core contract.
  api/
    app.py                   # root FastAPI app; routers are mounted dynamically per module manifest
```

**Hard rule**: nothing under `core/` may contain an `import` statement referencing `modules.*`. This is enforced by a CI lint rule (e.g., import-linter / custom AST check) — not just a convention — so an accidental dependency violation fails the build, not just code review.

The core does not know that "CRM" or "Production" exist. It knows: *a module is something that provides a manifest, a router, models, migrations, permissions, jobs, navigation entries, and settings schema* — and it can mount any number of things matching that shape.

### 4.4 The Module Contract (Plugin Interface)

Every module — CRM, Sales, Inventory, Purchasing, Production, Installation, Finance, Reports, Marketing, AI, and any future module — implements the same contract:

```
modules/
  <module_name>/
    manifest.py            # ModuleManifest: name, version, dependencies on other modules
    presentation/
      api/                  # FastAPI APIRouter(s) — this module's API namespace
      schemas/              # Pydantic request/response DTOs
    application/
      use_cases/            # application services / use-case classes (orchestrate domain + infra)
      event_handlers/        # subscribers: this module's reactions to OTHER modules' events
    domain/
      entities/              # pure business logic, no framework/DB imports
      value_objects/
      events.py               # domain events THIS module publishes (e.g., LeadCreated)
      repository_interfaces.py  # abstract interfaces the domain depends on
    infrastructure/
      models/                  # SQLAlchemy models implementing persistence for this module's entities
      repositories/            # concrete repository implementations (SQLAlchemy-backed)
      migrations/               # Alembic migration scripts scoped to this module
      jobs/                      # Celery task definitions this module registers
    permissions.py            # roles/actions this module introduces, registered with core RBAC
    navigation.py              # nav entries this module contributes to the frontend menu config
    settings_schema.py         # per-company configurable settings this module exposes (e.g., pipeline stages)
```

**What the manifest declares** (the actual plugin registration mechanism):

```
ModuleManifest(
    name="production",
    version="1.0.0",
    depends_on=["sales", "inventory"],     # core validates dependency modules are present & loaded first
    router=production_router,               # mounted at /api/production/*
    models=[WorkOrder, WorkOrderStage, ...],
    migrations_path="modules/production/infrastructure/migrations",
    permissions=PRODUCTION_PERMISSIONS,
    jobs=[start_work_order_task, ...],
    navigation=PRODUCTION_NAV_ENTRIES,
    settings_schema=ProductionSettingsSchema,
    event_subscriptions={
        "OrderApproved": [ReserveMaterialsAndQueueProductionHandler],
    },
)
```

**Module registration flow at startup**: the registry scans the `modules/` package (or a configured list, for environments wanting explicit allow-listing), validates each manifest, checks declared dependencies are present, mounts each router under `/api/<module_name>`, registers permissions with RBAC, registers Celery jobs, registers navigation/settings with the frontend config API, and wires event subscriptions into the event bus. **None of this requires editing core code** — it is core code, written once, that reads manifests generically.

A module can be disabled per company via the existing `companies.enabled_modules` configuration (revision 2) without being unmounted from the application process — the company-level toggle controls *visibility and authorization*, not whether the plugin is loaded. Whether a module is *installed at all* in a given deployment is controlled by which module packages are present/registered, independent of per-company enablement.

### 4.5 Clean Architecture Within Each Module

Every module is internally layered, dependencies pointing strictly inward:

```
Presentation  →  Application  →  Domain  ←  Infrastructure
  (depends on)     (depends on)   (depends  (depends on
                                    on nothing) Domain interfaces)
```

- **Domain** (innermost): entities, value objects, domain events, and repository *interfaces*. No imports from FastAPI, SQLAlchemy, Celery, or any other module. This is pure Python business logic — e.g., a `Deal` entity knows what stage transitions are valid; it does not know it's stored in Postgres.
- **Application**: use-case classes that orchestrate domain logic — e.g., `ApproveOrderUseCase` loads an order via a repository interface, calls domain methods, persists via the interface, and publishes an `OrderApproved` event. Application layer also contains this module's **event handlers** — its reactions to events published by other modules.
- **Infrastructure** (outermost, implements domain interfaces): SQLAlchemy models and repository implementations, Alembic migrations, Celery task implementations, calls to Supabase Storage, calls to the AI module's API, etc. This is where framework/DB-specific code lives.
- **Presentation**: FastAPI routers and Pydantic schemas. Translates HTTP requests into application use-case calls and use-case results into HTTP responses. Contains no business logic itself.

**Why this matters for this platform specifically**: domain logic (e.g., "what counts as a valid order approval," "how slab consumption is calculated") can be unit-tested with zero database or HTTP server running, which matters a lot once the AI module starts calling into the same use-cases (e.g., an AI-suggested reorder triggering the same `CreatePurchaseOrderUseCase` a human-driven API call would trigger) — the use case is reusable regardless of *what* triggered it.

### 4.6 Event-Driven Architecture (EDA)

#### 4.6.1 Purpose
Modules must react to each other's business outcomes (e.g., Production should start when an order is approved; Inventory should reserve stock when a quote is converted) **without importing each other's code**. Direct in-process calls between modules would violate plugin independence (Production would need to import Sales internals) and would make modules un-removable without breaking others. Events solve this: a module publishes a fact about what happened in its own domain; any number of other modules (zero, one, or many) may react, and the publisher never knows or cares who's listening.

#### 4.6.2 Event Bus (Core Infrastructure)
- Lives in `core/events/event_bus.py` — generic publish/subscribe mechanism, no knowledge of specific event names.
- **Phase 1 implementation**: in-process synchronous/async dispatch within the FastAPI application (sufficient for a single-deployment monolith with modest load).
- **Upgrade path**: the same publish interface can be backed later by Redis Pub/Sub, or a durable broker (e.g., the existing Celery/Redis infrastructure can carry events as tasks) if cross-process delivery, replay, or guaranteed-delivery semantics are needed — this is an infrastructure swap behind the same interface, not a redesign.
- Every event carries a standard envelope: `event_name`, `event_id`, `company_id` (mandatory — events are always tenant-scoped), `payload`, `occurred_at`, `published_by_module`.

#### 4.6.3 Representative Domain Events

| Event | Published by | Plausible subscribers |
|---|---|---|
| `CustomerCreated` | CRM | Marketing (attribution), AI (future profiling) |
| `LeadCreated` | CRM / Marketing | Sales (qualification), AI (lead scoring, future) |
| `QuoteCreated` | Sales | Reports, AI (future pricing suggestions) |
| `OrderApproved` | Sales | Inventory (reserve stock), Production (queue work order), Finance (expect invoice) |
| `InventoryReserved` | Inventory | Production, Reports |
| `SlabConsumed` | Production / Inventory | Inventory (deduct stock), Reports, AI (future yield optimization) |
| `ProductionStarted` | Production | Installation (scheduling lead time), Reports |
| `ProductionFinished` | Production | Installation (ready to schedule), Finance, Reports |
| `InstallationCompleted` | Installation | Finance (trigger invoicing), CRM (follow-up task), Reports |
| `PaymentReceived` | Finance | CRM (account status), Reports |

This list is illustrative, not exhaustive — each module's domain layer defines the authoritative event names it owns as development reaches that module's phase.

#### 4.6.4 AI Module as a Universal Subscriber
The future AI module is architected from day one as an **event consumer across the whole platform**, not a module other modules call into one-by-one. It subscribes to the events relevant to its capabilities — e.g., `InstallationCompleted` with attached site photos can trigger image analysis; `OrderApproved` volumes over time feed future forecasting models; document-bearing events trigger OCR/extraction jobs. Because this is event-driven, **AI capabilities can be added or expanded later by adding new subscriptions, without changing the publishing modules at all** — Sales does not need to know AI exists for AI to eventually react to `OrderApproved`.

#### 4.6.5 Event Handling Reliability
- Event handlers that do real work (especially anything touching AI, documents, or images) execute via **Celery tasks**, not inline in the publishing request's response cycle — publishing an event enqueues handler execution rather than blocking on it.
- Handler failures are logged and retryable (standard Celery retry semantics) without affecting the publishing module's own transaction success.
- Events are an integration mechanism for **cross-module side effects**, not a replacement for each module's own transactional integrity — a module still directly persists its own state changes via its own repository before publishing the fact that they happened.

### 4.7 API Namespacing and Mobile Parity

- Every module's presentation layer mounts its router at `/api/<module_name>/...` (e.g., `/api/crm/contacts`, `/api/production/work-orders`), per its manifest — giving each module a clean, independent API namespace with no risk of route collisions managed by hand.
- All authenticated access — web and future mobile — goes through the **same versioned REST API** (`/api/v1/...`). There is no server-rendered-only or session-cookie-only path that bypasses the API; Next.js calls the same endpoints a mobile client would, using the same JWT-based auth.
- This requires: stateless authentication (JWT, not server-side session state tied to a browser), all business operations exposed as API endpoints (no "admin console only" logic that mobile can't reach), and consistent pagination/error/response conventions across all modules' APIs so a mobile client can use one shared API client library against all of them.
- Practical implication for Phase 1: the API is designed and documented (OpenAPI, generated automatically by FastAPI) as the product surface — the web app is a consumer of it, not the other way around.

## 5. Database Architecture (carried forward, refined)

### 5.1 Tenancy Model (unchanged)
Single PostgreSQL database (Supabase), every tenant-owned table carries `company_id`, enforced by application-layer scoping + Postgres Row-Level Security as defense-in-depth. Rationale unchanged from revision 2.

### 5.2 Schema Ownership Under the Plugin Model
Each module's `infrastructure/models/` defines its own SQLAlchemy models and owns its own Alembic migration history (`infrastructure/migrations/`), satisfying "every module owns its migrations." All module migration scripts are still applied through a single unified Alembic migration chain at deploy time (the core's migration runner discovers and orders each module's migration scripts via the module registry), so the database remains one consistent schema even though ownership is split by module. A module being removed should, in principle, leave its tables intact (data is not silently dropped) unless an explicit uninstall/migration-down path is run — module removal is an operational decision, not an automatic deletion.

### 5.3 Core Cross-Module Tables (unchanged from revision 2, now explicitly core-owned)
`companies`, `users`, `user_company_roles`, `audit_log`, `documents`, `ai_jobs` remain core-owned tables (per §4.3, `companies` is treated as part of the core contract since every module depends on it). All other tables (`contacts`, `deals`, `work_orders`, `installation_jobs`, `invoices`, etc.) belong to their respective module's infrastructure layer, as listed in revision 2 §5.4.

### 5.4 Event Persistence (new)
An `event_log` core table records every published event (`event_id`, `event_name`, `company_id`, `payload`, `published_by_module`, `occurred_at`, `processed_by` per subscriber) — both for audit/debuggability ("why did Production start this work order?") and as the natural foundation if event delivery is later upgraded to a durable broker requiring replay.

## 6. Multi-Company Strategy (unchanged from revision 2)
Company as core entity with `enabled_modules` configuration; many-to-many user-company-role mapping with module-level permission overrides; company context derived from session/JWT, never client-supplied; cross-company reporting remains an explicit privileged permission. No changes required by this revision — the plugin/event architecture sits orthogonally to tenancy.

## 7. Security Architecture (carried forward, with plugin/event additions)

All revision 2 security measures (JWT auth, RBAC, RLS, TLS, secrets management, input validation, audit logging, rate limiting, backups, least privilege) remain in force. Additions for this revision:

- **Permission registration integrity**: since modules self-register their permissions with core RBAC, the core validates at startup that no module declares a permission name colliding with another module's, preventing accidental privilege confusion between, e.g., Sales and Finance "approve" permissions.
- **Event payload scoping**: every event is mandatorily tagged with `company_id`; the event bus rejects/refuses to dispatch any event missing tenant context, so cross-company data cannot leak through an event payload by omission.
- **Module boundary enforcement in CI**: an automated import-boundary check (core must not import modules; modules must not import each other's `domain`/`infrastructure` internals — only event payloads or explicitly published application-layer interfaces) runs in CI and fails the build on violation, not just on manual review.
- **API-as-the-only-door**: because mobile and web share the same API, there is exactly one authorization surface to secure and audit, rather than divergent web-only and mobile-only logic paths that could drift out of sync.

## 8. Deployment Architecture (carried forward, with event/worker additions)

Unchanged from revision 2 (containerized FastAPI + Celery workers + Next.js, Supabase-managed Postgres/Storage, managed Redis, staged environments, CI/CD with migration runs, monitoring). Addition for this revision:

- **Event handler execution** runs through the existing Celery worker pool — no new infrastructure category is introduced for EDA; it reuses the background-job infrastructure already planned for AI/document processing, sized accordingly as more modules add event subscriptions over time.
- **Module manifest validation step** added to CI/CD: before deploy, a startup check confirms all module manifests load, dependencies resolve, and no core→module import violations exist — catching a broken plugin contract before it reaches staging.

## 9. Module Roadmap (unchanged module list, ownership model clarified)

Same ten modules and phase sequencing as revision 2 (CRM → Sales → Inventory/Purchasing → Production → Installation → Finance → Reports → Marketing → AI), now explicitly understood as: each phase delivers one *plugin*, fully Clean-Architecture-layered, publishing and subscribing to the events relevant to it, registered through the manifest contract — not a folder added to a shared codebase with implicit coupling. The Foundation phase additionally must prove the **module registry, manifest contract, and event bus** with at least one real module (CRM) before Sales is built, so the second module validates that the contract truly required no core changes.

## 10. Risks (unchanged risks carried forward, new risks added)

| Risk | Mitigation |
|---|---|
| **Cross-company data leak** | App-layer scoping + Postgres RLS; isolation tests per module (unchanged) |
| **Module coupling creep** | Now concretely enforced: CI import-boundary linting forbids core→module and module→module internal imports; cross-module interaction must go through events or explicitly published interfaces |
| **AI workloads degrading core performance** | Event handlers and AI jobs run via Celery, never inline (unchanged, now formalized as the general event-handling rule, not just an AI-specific one) |
| **Over-engineering for current team/scale** (plugin + Clean Architecture + EDA is a lot of structure for 3 companies) | Mitigated by keeping Phase 1 event bus in-process/simple (no premature distributed broker); structure is justified by the explicit multi-year AI/multi-module roadmap, not adopted reflexively |
| **Event storms / unclear event ownership** as more modules subscribe to more events | Each event has exactly one publishing module (its domain owner); event names and payload shapes are defined once in the publishing module's `domain/events.py` and documented, not redefined ad hoc by subscribers |
| **Eventual consistency confusion** (e.g., `OrderApproved` triggers async inventory reservation — UI must not assume it's instant) | Frontend/API design must surface job/event-driven state transitions explicitly (e.g., order status field shows "reserving stock" before "confirmed"), not assume synchronous side effects |
| **Plugin contract becoming a bottleneck** if it's too rigid for a module's real needs | Manifest contract reviewed for completeness against the *first two* real modules (CRM, Sales) before assuming it generalizes to all ten |
| **Mobile-readiness assumed but unvalidated** until a mobile client actually exists | Treat the web frontend as a strict API consumer from day one (no backend shortcuts) so parity is structural, not something to retrofit when mobile work starts |
| **Underspecified per-module requirements** | Unchanged — validate each module's detailed requirements immediately before its phase, not all upfront |
| **Key-person dependency** | This document + per-module manifests + recorded event catalog serve as living architecture reference |

## 11. Development Phases (updated)

1. **Phase 0 — Validation** (no code): Confirm module list, per-company `enabled_modules`, and detailed CRM requirements with stakeholders. Confirm this architecture (plugin contract, Clean Architecture layering, EDA, API-first/mobile-parity) is the one to freeze.
2. **Phase 1 — Foundation & Architecture Proof**: Build the core host (registry, RBAC engine, audit, storage, event bus, DB session management) with **zero business modules**. Build the **CRM module** as the first real plugin end-to-end (Domain → Application → Infrastructure → Presentation), publishing its first real events (`CustomerCreated`, `LeadCreated`). Build the **Sales module** second, specifically to validate cross-module event subscription (Sales reacting to nothing yet, but publishing `QuoteCreated`/`OrderApproved` for future subscribers) and to prove the registry handles two modules with a declared dependency (`sales` depends on `crm`) without core changes.
3. **Phase 2 — Inventory + Purchasing**: First modules to *subscribe* to another module's event (`OrderApproved` → reserve stock), proving the consumer side of EDA.
4. **Phase 3 — Production**: Subscribes to `OrderApproved`/inventory events; publishes `ProductionStarted`/`ProductionFinished`/`SlabConsumed`.
5. **Phase 4 — Installation**: Subscribes to production completion events; publishes `InstallationCompleted`.
6. **Phase 5 — Finance**: Subscribes to `InstallationCompleted`/order events; publishes `PaymentReceived`.
7. **Phase 6 — Reports**: Cross-cutting; primarily a consumer of accumulated data and events across all prior modules.
8. **Phase 7 — Marketing**: Feeds `LeadCreated`-adjacent events into CRM.
9. **Phase 8 — AI module**: Built as a pure event subscriber plus its own document/image processing API namespace; validates that a module added late requires zero changes to the seven modules that already exist.
10. **Phase 9 — Mobile client**: Built directly against the existing versioned API — the first real test of API/mobile parity claims made in this document.
11. **Phase 10 — Hardening & launch**: Security review (including import-boundary and event-scoping checks), load/perf testing (including event-handler throughput under Celery), backup/restore drill, staged rollout per company.
12. **Phase 11 — Iteration**: Additional modules added purely via the established manifest/event contract.

---

## 12. Summary

This revision finalizes G-ERP's architecture as a **plugin-based core** (auth, RBAC, audit, storage, company registry, event bus — and nothing business-specific) hosting independently pluggable modules (CRM, Sales, Inventory, Purchasing, Production, Installation, Finance, Reports, Marketing, AI), each internally structured with **Clean Architecture** (Domain → Application → Infrastructure → Presentation) and integrated with its peers exclusively through **published domain events** rather than direct code dependencies. Every module exposes its own API namespace under a single versioned REST API that web and future mobile clients consume identically, with no backend shortcuts available only to the web app. The future AI module is designed from the outset as a cross-cutting event subscriber, able to gain new capabilities by subscribing to existing events without any change to the modules that publish them.

This is the architecture proposed for freeze. No application code has been written. Upon approval of this document, Phase 1 (Foundation & Architecture Proof, building the core host plus the CRM and Sales modules as the first validated plugins) is the recommended next step.
