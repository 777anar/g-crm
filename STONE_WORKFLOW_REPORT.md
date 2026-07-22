# Stone Fabrication Workflow — Phase 1 Report

_Date: 2026-07-22_
_Scope: Purchasing → Inventory → Production, Version 2.34.0, commit `bf8f882`._
_Audience: this is a business-logic explainer first, a code index second — each section states what problem is being solved for G-STONE's actual shop-floor operation before it names the table/endpoint that solves it._

---

## 1. Business Workflow Implemented

Before this phase, the application could track that a slab existed and that a work order existed, but it could not answer three questions a real stone fabrication business asks every day:

1. **"Is this specific slab spoken for, and by whom?"** — Previously, "reserved" was just a status word on a slab. Nothing recorded *which* order or customer it was reserved for, so there was no way to look at a slab and trace it to a job, or to look at a job and confirm exactly which physical slabs back it.
2. **"Where physically is this slab in its life, right now?"** — A slab's status jumped straight from "in a truck from the supplier" to "available to sell," with no room for the very real gap in between: it has arrived, but nobody has inspected it, graded it, or put it on a rack yet. And once it's cut, the outcome was binary in the system (sold or not) even though in reality a cut slab either becomes fully part of a customer's job *or* leaves a reusable offcut behind — two different, both valuable, outcomes that a shop needs to tell apart.
3. **"What is actually happening on the shop floor with this job, and who is accountable for it?"** — A work order had a coarse six-value status (queued/cutting/polishing/quality_check/completed/cancelled) and nothing else: no priority, no named operator, no record of which specific detailed stage (measuring? CNC? waterjet?) it was in, and no history of how it got there.

Phase 1 answers all three by building one continuous data trail that starts the moment a slab is delivered by a supplier and ends the moment it (or its offcut) is fully consumed by a customer's job:

```
Purchasing receives a slab
        │
        ▼
   received  ──(shelved/inspected)──▶  available (in stock)
        │                                   │
        │                          (explicit reservation
        │                           OR implicit via quote
        │                           acceptance)
        │                                   ▼
        │                               reserved ───────────────┐
        │                                   │                    │ (order cancelled /
        │                                   │ (work order        │  reservation released)
        │                                   │  created)           │
        │                                   ▼                    │
        │                             in_production ◀─────────────┘
        │                                   │
        │                      ┌────────────┼─────────────┐
        │                      ▼            ▼              ▼
        │                  consumed   offcut_created     scrap
        │                (fully used)  (remnant slab   (damaged/
        │                               registered,     wasted)
        │                               reservable
        │                               like any slab)
        ▼
      scrap (can also be scrapped straight off the truck)
```

Layered on top of that slab journey is the **order-side journey**: a customer order reaches "approved for production" → a Production Job (Work Order) is created against it → the job is triaged (priority, assigned operator, current shop-floor stage) → it moves through its coarse lifecycle to completion → every step along the way is written to a timeline anyone can read back later, in plain language, without digging through raw audit-log diffs.

This is the actual business value: a manager can now open one screen (`/production/{id}`) and answer "whose job is this, what material, what thickness/finish, who's cutting it, what stage is it at, is it on schedule, and what happened to it so far" — all from data the system already had to collect anyway, just never assembled or tracked with this level of granularity before.

---

## 2. Database Changes

All changes are **additive** — no existing column was renamed, no existing status value was removed, and no existing API response field changed shape. This was a deliberate constraint: the affected tables (`catalog_slabs`, `work_orders`) are live, in-use tables in a system already described as in production use by G-STONE GALLERY, so anything that could silently break an existing quote/order/work-order flow was avoided.

| Table | Change | Why |
|---|---|---|
| `catalog_slabs` | + `parent_slab_id` (nullable, self-referential FK) | Lets an offcut slab point back to the original piece it was cut from — pure lineage, no behavioral effect on a normal slab |
| `catalog_slabs` | + `is_offcut` (boolean, default `false`) | Lets inventory reports and the UI tell an offcut apart from an originally-received slab, even though it's otherwise a completely normal, independently reservable row |
| `catalog_slabs` | `status` vocabulary extended from 5 to 8 values | See §7 — `received`, `offcut_created`, `consumed` added; `available`, `reserved`, `in_production`, `sold`, `scrap` untouched |
| `work_orders` | + `priority` (text, default `normal`, indexed) | See §8 |
| `work_orders` | + `current_stage_id` (nullable FK to the new `production_stages` table) | See §8 — deliberately a *separate* dimension from the existing `status` column, not a replacement for it |

One Alembic migration carries all of this: `backend/migrations/versions/67e0a8a55a5a_stone_fabrication_workflow_phase1.py`, generated via `alembic revision --autogenerate` and applied to and verified against the real dev database (`alembic check` reports no drift). Because SQLite (the dev database engine) cannot `ALTER TABLE ... ADD CONSTRAINT` directly, the two new foreign keys (`catalog_slabs.parent_slab_id`, `work_orders.current_stage_id`) are added via `batch_alter_table`, the same pattern already established in this codebase's `fcaddc974e1c` migration for an identical constraint-on-SQLite limitation.

---

## 3. New Tables

### `catalog_slab_reservations` (owned by the Catalog module)
The durable record behind Material Reservation (§6). Deliberately lives in Catalog, not Production or Orders, even though a reservation is conceptually "for an order" — because Catalog is the one module every other module already depends on, and putting the reservation table anywhere downstream (Orders, Production) would force Catalog to depend back on them, inverting the module dependency graph this codebase is careful never to invert (`CLAUDE.md`'s one architectural rule).

| Column | Purpose |
|---|---|
| `slab_id` | Which slab is reserved (real FK — Catalog owns Slab) |
| `order_id`, `order_item_id` | What it's reserved for — **plain UUID columns, no FK constraint.** This is the same "polymorphic reference, application-layer only" pattern already used elsewhere in this codebase (`documents.related_entity_id`, `crm_leads.campaign_id`) specifically so Catalog never has to import or depend on the Orders module just to record who a reservation is for |
| `status` | `active` → `released` (cancelled/reassigned) or `consumed` (the job finished) |
| `reserved_by`, `reserved_at`, `released_at` | Who and when, for accountability |
| `notes` | Free text |

### `production_stages` (owned by Production)
The configurable shop-floor pipeline (§8). Per-company, so two companies (G-STONE GALLERY, KORONA PREMIUM, NEOLITH BAKU) can each run their own stage list without affecting each other. `name` + `sort_order` + `is_active` (hide without deleting history).

### `work_order_events` (owned by Production)
The timeline backbone (§9). One row per meaningful change to a Production Job: `event_type` (`created`/`status_changed`/`stage_changed`/`priority_changed`/`operator_assigned`), `from_value`/`to_value` as human-readable strings (a stage's *name*, not its id — so the timeline never has to re-join anything to render), `notes`, `changed_by`, `changed_at`.

---

## 4. New APIs

All new endpoints reuse the existing two Production permissions (`production:read`/`production:write`) and Catalog's existing (`catalog:slabs:read`/`catalog:slabs:write`) — no new permission strings were introduced, keeping RBAC simple rather than fragmenting it further for what are, from a permissions standpoint, just more actions on the same two resources.

**Catalog (Material Reservation + offcuts):**
| Method | Path | What it does |
|---|---|---|
| `GET` | `/catalog/slabs/{id}/reservations` | Full reservation history for one slab |
| `POST` | `/catalog/slabs/{id}/reserve` | Reserve a slab for an order item (§6) |
| `POST` | `/catalog/slabs/reservations/{id}/release` | Release an active reservation |
| `GET` | `/catalog/reservations?order_id=` | All reservations for an order — backs the Production Job page |
| `POST` | `/catalog/slabs/{id}/offcuts` | Register a remnant from an `in_production` slab (§7) |

**Production (Job tracking, stages, timeline):**
| Method | Path | What it does |
|---|---|---|
| `GET`/`POST` | `/production/stages` | List (auto-seeds 8 defaults) / create a stage |
| `PATCH` | `/production/stages/{id}` | Rename / reorder / hide a stage |
| `GET` | `/production/{id}/job` | The full enriched "Production Job" view (§8) |
| `GET` | `/production/{id}/timeline` | The event history (§9) |
| `PATCH` | `/production/{id}` | Update due date / notes |
| `POST` | `/production/{id}/priority` | Change priority |
| `POST` | `/production/{id}/assign` | Assign / unassign an operator |
| `POST` | `/production/{id}/stage` | Move to a different pipeline stage |

`POST /production` (create) was extended to accept optional `priority`/`due_date` at creation time, on top of its existing `order_id` body field.

---

## 5. Frontend Pages

- **`/production`** (list) — gained **Priority** and **Due Date** columns alongside the existing Work Order #/Status/Order/Created columns.
- **`/production/{id}`** (detail) — rewritten from a bare status-tracker into the full Production Job view:
  - Customer and Project shown as real links (`/crm/customers/{id}`, `/sales/projects/{id}`), not raw ids.
  - An editable panel: Priority (dropdown), Assigned Operator (dropdown sourced from `listCompanyUsers()`, same pattern already used for CRM's Assigned Manager picker), Current Stage (dropdown sourced from the company's configured stages), Due Date, Notes.
  - The consumed-slabs table gained **Material**, **Thickness**, and **Finish** columns (previously only slab number/description/quantity/area).
  - A new **Timeline** section rendering every event in order, in plain language (e.g. "Stage changed from Measuring to CNC", "Priority changed from high to urgent"), with a special-cased first-stage-move message ("Stage set to CNC") to avoid an awkward "changed from — to CNC" on the very first move.
- **`/production/stages`** (new) — a settings page to add, rename, and hide stages, following the same list+inline-create+toggle pattern already established by Catalog's Warehouses settings page. Reachable from a new "Production" group on `/settings`.

All new UI strings are translated across all three locales (az/ru/en), including the slab-status labels, which were also **relabeled** for clarity per the requirement's own vocabulary (`available` now displays as "In Stock", `scrap` as "Scrapped") — a display-only change; the underlying stored value is untouched.

---

## 6. Reservation Logic

**The problem this solves:** before this phase, "reserving" a slab meant nothing more than flipping its `status` field to `"reserved"`. That told you a slab *was* reserved, but not *for what* — there was no record linking the reservation to a specific order or order item. Two staff members could, in principle, both believe they'd claimed the same slab, and the only thing standing between them was whoever wrote the status field last.

**How it works now:**
1. `POST /catalog/slabs/{id}/reserve` takes `{order_id, order_item_id}`. It looks for an existing **active** reservation on that slab.
   - If one exists for the *same* order item, it's a no-op — calling reserve twice for the same item is safe (idempotent), which matters because a UI retry or a double-click shouldn't produce an error.
   - If one exists for a *different* order item, it's rejected with `409 Conflict` — this is the actual double-booking guard, checked and enforced inside a single use-case execution (the same "check-then-set in one transaction" pattern this codebase already relies on for PO-number sequences and Sales' own pre-existing quote-acceptance slab check — there is no partial-unique-index trick here, and there didn't need to be one, because nothing else in this codebase uses one for a comparable invariant either).
   - Otherwise, it creates the reservation row and moves the slab from `available` to `reserved`.
2. **Where reservations come from in practice** — there are two paths, both landing in the same table:
   - **Explicit**: a staff member calls the reserve endpoint directly (e.g., picking a replacement slab for an item that didn't come with one from the quote).
   - **Implicit / adopted**: when a quote is accepted, Sales' existing logic (unchanged) already moves any quoted slab to `reserved`. When an Order is later created from that accepted quote, the new code in `CreateOrderUseCase` now also **backfills** a formal reservation row for every slab-linked item it copies — using a `require_available=False` flag that skips the availability re-check (the slab is already known to be reserved; this call is just recording the paperwork for it). This one small addition gives 100% reservation coverage for every slab that has ever been quoted and ordered, without touching a single line of the Sales module.
3. **Release** (`POST /catalog/slabs/reservations/{id}/release`) marks the reservation `released` and, only if the slab is *still* `reserved` (nothing else has moved it on in the meantime, e.g. into production), returns it to `available`.
4. **Consumption** happens automatically, not via a direct API call — see §8: when a Production Job completes, every reservation tied to its items is marked `consumed`.

---

## 7. Slab Lifecycle

**The problem this solves:** a slab's life in a real fabrication shop has more steps than "available" and "sold," and treating it as a two-state object hid real business distinctions a warehouse manager actually cares about — has this been inspected yet? did this cut leave anything usable behind?

**The eight statuses and what each one means on the shop floor:**

| Status | Real-world meaning | How a slab gets here |
|---|---|---|
| `received` | Just arrived from a supplier via Purchasing; not yet inspected or shelved | Purchasing's `POST /purchasing/purchase-orders/{id}/lines/{id}/receive` now creates the slab in this status instead of jumping straight to `available` |
| `available` | Inspected, shelved, ready to be sold/reserved ("In Stock" in the UI) | Manual slab creation (unchanged, defaults here directly — a staff member typing "here's a slab in my warehouse" is asserting it's already usable), or an explicit shelve-to-stock `PATCH .../status` from `received` |
| `reserved` | Committed to a specific order item, not yet being cut | Reservation (§6) |
| `in_production` | Actively on the cutting/CNC/waterjet floor | A Work Order is created against the order (§8) |
| `offcut_created` | The original slab's productive life ended by leaving a usable remnant | `POST /catalog/slabs/{id}/offcuts` — only legal while the parent is `in_production` |
| `consumed` | Fully used up, nothing left over | A Work Order completes (§8) — this is what a slab becomes by default, not `sold` |
| `sold` | Reserved for backward compatibility / non-fabrication direct-sale flows | Untouched from before this phase — still reachable, just no longer the completion target for fabrication jobs |
| `scrap` | Damaged or wasted, reachable from almost anywhere | Manual, at any point |

**The transition graph** (`is_valid_slab_transition` in `modules/catalog/domain/value_objects.py`) is a directed graph, not "any status to any status" — a `consumed` slab can never accidentally bounce back to `available`, but `scrap` is reachable from nearly every non-terminal state (a slab can break at any point). The three new statuses were added by *extending* the existing graph, never replacing an edge that already existed, which is why every pre-existing quote/order/work-order test kept passing unchanged.

**Offcuts** are the one genuinely new physical-inventory concept: `POST /catalog/slabs/{id}/offcuts` takes a parent slab that is currently `in_production`, and creates a **brand new, completely normal `Slab` row** for the remnant (own slab number, own dimensions, status `available`, flagged `is_offcut=true` with `parent_slab_id` pointing at the original). The offcut is then reservable and sellable exactly like any other slab — the business value is that a shop no longer has to either throw away a usable leftover piece or track it on paper outside the system.

---

## 8. Production Workflow

**The problem this solves:** a Work Order previously had one status field doing three jobs at once — tracking coarse progress, implying (but not recording) priority, and offering no way to know who was working on it or what specific station it was at. Real shop floors triage work (some jobs are urgent, some aren't), assign named operators, and move a physical piece through a sequence of specific stations that isn't the same as "queued → cutting → polishing" (a piece might sit at Measuring, then Design, then CNC, then Waterjet, then Cutting, then Polishing, then Quality Control, then be Ready for Installation — eight real steps, not four).

**Two independent dimensions, on purpose:**
1. **Status** (unchanged): `queued → cutting → polishing → quality_check → completed`, with `cancelled` reachable from any non-terminal point. This is the coarse lifecycle that drives real side effects — it's what cascades the slab to `in_production`/`consumed`/`available`, what advances the parent Order to `ready`, and what completes/cancels the job. This was left completely untouched because it's load-bearing, tested, and correct.
2. **Stage** (new): a pointer at one row in the company's own configurable `production_stages` list. This tracks *where on the floor* the physical piece actually is, independent of the coarse status above. A job can be `status: cutting` and simultaneously at stage "CNC" or "Waterjet" — the stage doesn't gate or drive the status, and moving it doesn't cascade anything. Stages can move **backward** as well as forward, deliberately unconstrained by a transition graph, because real fabrication shops send a piece back for rework and the system shouldn't get in the way of recording that honestly.

**Priority** (`low`/`normal`/`high`/`urgent`) is a simple triage label, not a numeric weight, chosen specifically so it reads the same on a printed job card as it does in a conversation with an operator ("this one's urgent"). It can be set at job creation or changed at any time via its own endpoint.

**Operator assignment** is validated against actual company membership (the same `UserCompanyRole` check already used for CRM's Assigned Manager field) — assigning a job to a UUID that isn't a real member of the active company is rejected, not silently persisted.

**The "Production Job" view** (`GET /production/{id}/job`) is the single call that assembles everything a shop floor manager needs to see about a job: who it's for (customer, project), what it's made of (material, thickness, finish — per reserved slab), how urgent it is, who's on it, and where it currently sits in the pipeline. This was built as a separate enriched endpoint rather than changing the plain `GET /production/{id}` response, so nothing that already consumed the old shape had to change.

---

## 9. Timeline Implementation

**The problem this solves:** the only history of what happened to a job previously lived in the generic core audit log — technically complete, but stored as opaque diff blobs (`{"status": {"old": "cutting", "new": "polishing"}}`) meant for compliance/forensics, not for a manager glancing at a job's history to understand its story.

**How it works:** every mutation that matters to a job's story — its creation, every status change, every stage move, every priority change, every operator (re)assignment — appends one row to `work_order_events`. Each row is deliberately **denormalized and human-readable at write time**: `from_value`/`to_value` store the display string (a stage's *name*, a priority's *label*) rather than an id, specifically so the timeline UI can render directly from this table without a second round of joins or lookups at read time. `GET /production/{id}/timeline` returns these in chronological order; the frontend renders each one through an i18n template (`"Stage changed from {from} to {to}"`), with one special case for a job's very first stage assignment (no meaningful "from" value to show) rendered as "Stage set to {to}" instead of the more awkward generic phrasing.

This table is **additive to, not a replacement for**, the mandatory core audit log — see §10. A job's timeline is a curated, production-specific narrative; the audit log remains the authoritative, uniform, cross-module compliance record.

---

## 10. Audit Implementation

This codebase has one cross-cutting rule that applies to every write action in every module, with no exception carved out for this feature: **every write must both record an entry in the append-only `core.audit_log` (via `record_audit(...)`) and publish a domain event on the internal event bus.** Phase 1 follows this exactly:

- Every new use case — `CreateSlabReservationUseCase`, `ReleaseSlabReservationUseCase`, `CreateOffcutUseCase`, `CreateProductionStageUseCase`, `UpdateProductionStageUseCase`, `UpdateWorkOrderPriorityUseCase`, `AssignWorkOrderOperatorUseCase`, `UpdateWorkOrderStageUseCase`, `UpdateWorkOrderUseCase` — calls `record_audit(...)` with a module name, action string (e.g. `"slab_reservation.created"`, `"work_order.stage_changed"`), entity type/id, and a diff.
- Every new use case also publishes a named domain event (`SlabReservationCreated`, `SlabReservationReleased`, `SlabReservationConsumed`, `SlabOffcutCreated`, `WorkOrderStageChanged`, `WorkOrderPriorityChanged`, `WorkOrderOperatorAssigned`, `ProductionStageCreated`) on the same event bus every other module's writes go through.
- The new `work_order_events` table (§9) sits **alongside** this, not instead of it — it exists because a production-specific, denormalized, easy-to-render history is a genuinely different need from a generic, uniform, cross-module audit trail, and the codebase already draws that same distinction elsewhere (e.g., Purchasing's `goods_receipts` table is itself a domain-specific record layered on top of, not replacing, the generic audit log).

In short: nothing in this feature gets a lighter audit trail than any other write action in the application — it gets the same mandatory generic layer, plus one additional, purpose-built layer specifically for the "show a manager this job's story" requirement.

---

## 11. Tests Added

**30 new backend tests, all passing, bringing the full suite to 660/660 (630 prior + 30 new).**

**`tests/catalog/test_slab_reservations.py` (11 tests)** — Material Reservation and offcut tracking:
- `test_reserve_slab_moves_status_and_creates_reservation` — the basic happy path
- `test_reserve_slab_twice_for_same_item_is_idempotent` — re-reserving the same item is a safe no-op
- `test_reserve_slab_already_reserved_for_another_item_returns_409` — **the double-booking guard**
- `test_reserve_slab_not_available_returns_409` — can't reserve a scrapped/otherwise-unavailable slab
- `test_release_reservation_returns_slab_to_available` — release, then confirm it's reservable again
- `test_list_reservations_for_order` — the order-scoped reservation list
- `test_slab_received_must_move_to_available_before_reservable` — the `received` gate
- `test_received_slab_can_be_scrapped_directly` — damage discovered on arrival, before shelving
- `test_create_offcut_requires_slab_in_production` — rejects offcut registration on a non-`in_production` slab
- `test_create_offcut_from_in_production_slab` — the full offcut flow, including that the new offcut is itself reservable
- `test_reservations_are_scoped_to_company` — a reservation created in one company is invisible/unreachable from another

**`tests/production/test_stages.py` (5 tests)** — configurable stages:
- `test_list_stages_seeds_stone_fabrication_defaults` — the 8 defaults, in order, on first access
- `test_list_stages_is_idempotent_after_seeding` — seeding only happens once
- `test_create_custom_stage` — appending a company-specific stage
- `test_rename_and_hide_stage` — editing and hiding without deleting
- `test_stages_are_scoped_per_company` — two companies get independently seeded, disjoint stage sets

**`tests/production/test_work_order_tracking.py` (13 tests)** — Production Job tracking, stages, timeline:
- `test_create_work_order_with_priority_and_due_date` / `test_create_work_order_defaults_priority_to_normal` — creation-time fields
- `test_update_work_order_priority` / `test_update_work_order_priority_rejects_invalid_value` — priority updates and validation
- `test_assign_operator_requires_company_member` / `test_assign_and_unassign_operator` — operator validation and assignment
- `test_update_work_order_due_date_and_notes` — the mutable-fields PATCH
- `test_move_work_order_through_stages` / `test_move_to_unknown_stage_returns_422` — stage transitions, including backward moves and rejection of a foreign stage id
- `test_timeline_records_creation_priority_and_status_changes` — timeline ordering and event-type sequencing
- `test_cancel_work_order_releases_reservation_and_records_timeline_notes` — cancellation cascades to reservation release, with the cancellation reason captured in the timeline
- `test_production_job_detail_shows_customer_project_and_material` — the enriched job view's correctness
- `test_completing_work_order_marks_reservation_consumed` — completion cascades to `consumed` (not `sold`) and reservation `consumed`

**1 new test in `tests/orders/test_orders.py`** — `test_create_order_adopts_reservation_for_slab_linked_item`, confirming that creating an Order from an accepted quote backfills a `SlabReservation` row for every slab-linked item without re-validating or disturbing the slab's already-`reserved` status.

**One existing test was updated, not just left to fail**: `test_full_work_order_lifecycle_completes_order_and_sells_slab` in `tests/production/test_work_orders.py` was renamed to `..._and_consumes_slab` and its final assertion changed from `slab.status == "sold"` to `slab.status == "consumed"`, reflecting the deliberate, documented behavioral change in §8/§7.

**Beyond the automated suite**, this feature was verified with a live end-to-end smoke test against the actually-running application and the real dev database (received → shelved → reserved, with both the not-yet-shelved block and the double-booking conflict deliberately triggered and confirmed → order created with reservation adoption confirmed → work order created with priority/due date → stage/operator/priority updates → full status lifecycle to `completed` with the slab confirmed `consumed` and the reservation confirmed `consumed` → a second slab driven to `in_production` and an offcut registered from it), and with a Playwright pass over the actual rendered frontend (production list, stages page, job detail page) confirming zero console/runtime errors and correct rendering of every new field.

---

## 12. Remaining Limitations

Honest gaps left open in this phase, by scope decision rather than oversight:

- **No Kanban/board view for Production Jobs by stage.** The stage concept is fully functional (assign, move, track, timeline) but there is no visual board (unlike Installation's existing Kanban page) to see all jobs grouped by current stage at a glance. Would be a natural, low-risk frontend-only follow-up.
- **No drag-and-drop stage reordering.** Stages can be reordered by editing `sort_order` directly (not currently exposed in the UI at all — only rename/hide are), so reordering today would require a direct API call, not a UI action.
- **No reservation UI outside the Production Job page.** A staff member cannot browse "all active reservations" or reserve/release a slab directly from the Catalog/Inventory slab list or an Order's detail page — the reservation endpoints exist and are used internally (adoption, job cascades), but there's no dedicated "reserve this slab for this order" button anywhere in the UI yet. Today, explicit reservation is an API-only capability; the UI path to a reservation is still exclusively via quote acceptance.
- **`sold` and `consumed` now coexist as two valid terminal states** with overlapping real-world meaning for a shop that occasionally sells a slab as-is without fabricating it. This is intentional (keeps every pre-existing flow that used `sold` working unchanged) but does mean the two statuses' exact boundary is a convention, not something the system enforces — nothing stops a future direct-sale feature from also choosing `consumed` by mistake.
- **No offcut-area or dimension validation.** `POST /catalog/slabs/{id}/offcuts` accepts any length/width for the new offcut; there's no check that it's smaller than the parent slab or physically plausible. This is a data-entry trust boundary, same as the rest of this codebase's slab dimension fields.
- **No notifications or alerts on priority/stage change.** An `urgent` job or a job moved to "Quality Control" doesn't trigger any notification to anyone — the timeline is pull (someone has to open the job page to see it), not push.
- **Permissions stayed coarse.** Every new endpoint reuses the existing `production:read`/`production:write` and `catalog:slabs:read`/`catalog:slabs:write` — there's no finer-grained permission distinguishing, say, "can change priority" from "can reassign the operator." Consistent with this module's existing permission granularity, but worth revisiting if role requirements get more specific.
- **No bulk operations.** Reserving multiple slabs at once, or moving multiple jobs to a new stage together, both require one API call per item — there's no bulk endpoint, matching how the rest of this codebase (aside from the Customer list's bulk actions) generally works today.
- **Mobile client parity is unvalidated**, same pre-existing caveat as the rest of this application — nothing in this phase was designed against or tested with an actual mobile client.

None of these are regressions or defects in what shipped — they are the deliberately-scoped boundary of "Phase 1," left for a follow-up phase to pick up with full context of what's already in place.
