# Changelog

All notable changes to this project are documented in this file. See [ROADMAP.md](ROADMAP.md) for full delivery narratives, rationale, and what's next; this file is the terse, dated summary.

## [2.20.0] — 2026-07-14 — Shareable/Persisted List Filters

Closes the next Version 1.1 item per the roadmap's own sequencing (pagination in 2.19.0, filter persistence here): Customers and Leads filter state (status/channel, search, sort) lived only in component state, so a filtered view could never be bookmarked or shared via URL. Frontend-only, no backend changes.

### Added
- New shared `useUrlFilters` hook (`frontend/lib/use-url-filters.ts`) — two-way syncs a list page's filter state with its URL query string via `router.replace` (no extra browser-history entries), reading the URL once on mount to hydrate initial state.
- Customers list page filters reflected in the URL: `?status=&search=&sort=&archived=1`.
- Leads list page filters reflected in the URL: `?channel=&search=&sort=`.

### Changed
- Both pages split into a thin default-export wrapper plus a `<Suspense>`-wrapped inner component, required by Next.js App Router whenever a statically-generated page calls `useSearchParams()`.

### Verification
Full backend suite passing (537/537, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes, `/crm/customers` and `/crm/leads` still statically prerendered), and a live Playwright smoke test confirming: setting filters updates the URL, navigating directly to a filtered URL restores the same filter state and results, and clearing filters returns the URL to its bare path — on both Customers and Leads, zero console errors.

## [2.19.0] — 2026-07-14 — "Load More" Pagination for Customers & Leads

Closes the last open Medium-priority Version 1.1 item: `GET /crm/customers`/`GET /crm/leads` have had a correct cursor-pagination contract all along, but neither list page ever consumed it — both silently capped at the default `limit=25`. Frontend-only, no backend changes.

### Added
- "Load more" button on the Customers and Leads list pages, wired to the existing `next_cursor`/`cursor` contract.
- Shared `common.loadMore` translation key across all three locale files (previously only existed under the `catalog` namespace).

### Fixed
- **Real bug found via live Playwright testing, not by reading code**: the "Load more" pattern being copied from the existing Catalog Materials page had a stale-closure bug — `reload`'s `useCallback` read a `cursor` state variable deliberately excluded from its dependency array, so `reload` was never recreated when `cursor` changed. Clicking "Load more" always re-fetched page one and appended it again, duplicating all rows forever and never reaching page two. This bug had already shipped, unnoticed, on the Materials page itself. Fixed at the root in all three pages (Customers, Leads, Materials): removed the redundant `cursor` state and changed `reload` to accept the cursor as an explicit call-time argument instead of reading it from a closure.

### Verification
Full backend suite passing (537/537, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), and a live Playwright smoke test against a freshly seeded dev database (30 customers, 30 leads, 30 materials) confirming the fix on all three pages — reproduced failing before the fix (duplicate rows, React key warnings) and passing after.

## [2.18.0] — 2026-07-13 — Full-App UX Audit

A from-scratch audit of every visible screen from a real G-STONE office employee's perspective — six parallel research passes covering every page and locale key. Frontend-only; no new module, no business-logic changes.

### Fixed
- **Global**: every date in the app rendered in English regardless of locale (`lib/format.ts` hardcoded `"en-US"`) — now reads the active locale via a new `activeDateLocale()` helper. Same fix applied to the Installation Calendar's month header and `charts.tsx`'s tooltip number formatting.
- Reports' `CategoryBarChart`/`TrendChart` showed raw English "No data for this period." on any empty date range across all five Reports pages — added the `emptyLabel` prop `StatusBarList` already had.
- Illegible dark-mode section headers (`bg-text-primary` + `text-white`, near-white-on-white) on CRM Task, Finance Invoice, Order, and Sales Quote builder detail pages — switched to `bg-primary`.
- Orders/Production/Installation/Finance Invoice detail pages each had a toggle button and confirm button sharing the exact same cancel-action label — the toggle now hides once the confirm card is open.
- Silent failures on write actions across the Sales Project workspace, Quote builder, Installation Kanban, and Installation Crews — none of these had `try/catch`, unlike every page Version 2.9.1 already covered. All now surface errors via toast/inline error.
- Raw UUIDs shown instead of names/numbers: Orders list, Order/Work-Order/Invoice detail pages, and the Material Prices table (which also had the wrong data under a mismatched "Currency" header) — resolved via client-side lookups against existing `GET`-by-id endpoints.
- ~30 untranslated English strings on the Communication Integrations page (credential field labels, provider dropdown, Queue/Diagnostics table values).
- Real mistranslations: Leads' `qualified` status, a Sales item type ("Moydadır" → "Lavabo dolabısı"), `projectType_stairs`/`itemType_stairs` inconsistency, Tasks' `recurrenceInterval`.
- Finance Expense/Invoice due-date fields used free-text inputs with an English placeholder instead of native date pickers; Expense category filter reused the generic "all statuses" key instead of a dedicated one.
- Material creation form's Material Type dropdown showed raw English options inside an Azerbaijani form.
- Customer detail page's two note boxes shared identical placeholder text; Customer profile's "Layihələr" tile was mislabeled "via Production"; Dashboard's "Gecikən layihələr" section linked to Orders, not Projects (renamed to match); login's company-role badges showed a raw backend role string; Tasks list wasn't sortable/searchable like its sibling pages; a Task's "Related to" link showed the generic word "Customer" instead of the actual name.

### Removed
- Dead/orphaned translation keys across all three locale files: `customerNew.type`/`customerProfile.type`/`customers.tableType`/the `customerType` namespace (closing a Version 1.1 backlog item verbatim), `dashboard.notifications`, `catalog.title`/`subtitle`/`tabSlabs`, `nav.quotes`, `orders.prodStatus_unassigned`/`instStatus_unassigned`, `tasks.relatedCustomer`.

### Deferred
Sales Photos tab shows captions only (no image thumbnails); Material detail has no inline spec editing; Slabs/Price-List material pickers aren't searchable; Reports KPI cards show no currency unit; Installation's tab bar isn't the shared `SectionTabs` component; per-channel badge colors — each recorded as out of proportion for this pass or in conflict with an existing convention, not silently skipped.

### Verification
Full backend suite passing (537/537, unchanged — no backend files touched), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes), live smoke test against the real dev database and running backend.

## [2.17.0] — 2026-07-13 — Assigned Manager Picker

Closes the highest-priority remaining Version 1.1 item: the Customer form/profile had no real way to assign a manager, despite the backend fully validating the field since Phase 2.

### Added
- "Assigned Manager" dropdown (backed by `GET /api/v1/core/companies/users`) on the Customer creation form.
- The Customer profile page's manager field is now an editable dropdown instead of a raw UUID string.
- Toast confirmations on the Customer detail page for status change, manager change, note add, and the profile-notes save — the page previously had no `useToast` calls at all.
- 2 new backend tests covering explicit manager un-assignment and confirming an unrelated field update doesn't clear an existing assignment.

### Fixed
- `UpdateCustomerUseCase` (backend) could never actually clear `assigned_manager_id` — a PATCH body with `assigned_manager_id: null` was indistinguishable from the field being omitted entirely, since both read as Python `None`. A `clear_assigned_manager` flag, derived from `"assigned_manager_id" in payload.model_fields_set`, now makes "explicitly cleared" distinguishable from "not sent" for this one field, without changing PATCH-omission semantics for any other Customer field. Found via a live smoke test against the running dev API, not the automated suite.

### Verification
Full backend suite passing (537/537), frontend `tsc --noEmit` clean, frontend production build clean, live smoke test against the real dev database and running backend.

## [2.16.0] — 2026-07-10 — CSV Export for Customers & Leads

Closes the last Version 1.2 roadmap item never picked up: a standard CRM expectation (offline reporting, accounting handoff, marketing list pulls) that had been consistently deprioritized in favor of the Version 2.0+ module chain since 2026-07-01.

### Added
- `GET /api/v1/crm/customers/export` and `GET /api/v1/crm/leads/export` — CSV downloads honoring the exact same filters as their respective list endpoints (status/lead-source/search/sort for customers; status/channel/search/sort for leads), gated by the existing `crm:customers:read`/`crm:leads:read` permissions (no new permission introduced). Output is UTF-8 with a leading BOM so Excel renders Azerbaijani/Cyrillic characters correctly. Capped at 10,000 rows.
- "Export CSV" button on both the Customers and Leads list pages, next to the column-visibility menu, downloading the currently-filtered view via the existing `apiDownload` blob-download helper (the same mechanism Reports' PDF/Excel export and Sales' Quote PDF already use).
- 6 new backend tests (CSV shape, filter-respecting content, 401 without auth) across `test_customers_api.py`/`test_leads_api.py`.

### Verification
Full backend suite passing, frontend `tsc --noEmit` clean, frontend production build clean.

## [2.15.0] — 2026-07-10 — Sprint 6: Operational Dashboard Redesign

Replaces the generic CRM stats dashboard (customer/lead counters) with an operations-first view answering "what should our team do today?" — no new module, entirely inside the existing Dashboard page plus one small Sales endpoint to back it.

### Added
- `GET /api/v1/sales/measurements` — a company-scoped, date-range-filterable list of `ProjectItemMeasurement` rows (`ProjectItemMeasurementRepository.list_for_company`), backing the "measurements today" KPI. 1 new backend test (date-range filtering).
- Dashboard: time-of-day greeting ("Sabahınız xeyir" / afternoon / evening) using the logged-in user's real first name via `me()`, replacing the generic "Welcome back" + role line.
- Dashboard: four daily-ops KPI cards — measurements today, work orders in production, installations scheduled tomorrow, overdue work (overdue tasks + overdue orders combined).
- Dashboard: five new sections — Today's Tasks, Upcoming Installations, Overdue Projects (orders past their scheduled production/installation date), Notifications (merged task + installation notifications, newest first), and Recent Inquiries (replaces the old raw Leads table with the same data reframed as inbound inquiries).

### Changed
- Dashboard no longer shows raw customer/lead counters (active/archived customers, open/converted leads, leads-by-channel) — that pipeline-counter view is superseded by the daily-ops framing; the underlying Customer/Lead data and CRM screens are unaffected.
- `frontend/lib/api/sales.ts` gained `listMeasurementsForCompany()`; `az.json`/`ru.json`/`en.json`'s `dashboard` keys were rewritten to match the new sections (old `statActiveCustomers`/`myTasks`/`customersByStatus`-style keys removed, replaced with the new greeting/stat/section keys).

### Verification
Full backend suite passing, frontend `tsc --noEmit` clean, frontend production build clean.

## [2.14.0] — 2026-07-10 — UX & Production Polish Sprint

A frontend/wording-only audit pass ahead of daily use by G-STONE GALLERY's office staff — no new module, no business-logic or API changes.

### Changed
- The English word "Lead" (used untranslated inside otherwise fully Azerbaijani UI text — page titles, buttons, empty states, toasts, AI recommendation labels) replaced with "Potensial müştəri" consistently across the Dashboard, Leads, Reports, Quick Create, and AI Dashboard sections of `az.json`, matching the term the Leads/CRM tabs already used in a few spots.
- Generic "CRM" wording removed from the Dashboard subtitle and the Communication inbox's "not yet linked" message in all three locales (`az.json`/`ru.json`/`en.json`), replaced with plain "recent activity" / "customer record" phrasing.
- Fixed a real mistranslation: `subtotal` in `az.json` (Sales/Orders/Finance) was `"Arayış"` (Azerbaijani for "certificate/reference"), not a subtotal — corrected to `"Aralıq məbləğ"`.
- `catalog.isDefault` in `az.json` used the untranslated English word "Default" while the equivalent table header already said "Standart" — made consistent.
- The literal CRM-metaphor translation "Boru Kəməri" ("pipeline" as in oil pipeline) replaced with "proses"/"satış prosesi" wording across the AI Dashboard and Reports subtitle — the office-staff-facing term for "deals in progress," not a literal physical pipeline.
- Seed script's default owner account full name changed from the placeholder-sounding `"Platform Owner"` to `"G-STONE Admin"` (`backend/scripts/seed.py`) — this name is user-visible (e.g. "Welcome back, ...") the moment anyone signs in with the seeded account.
- Two English placeholder examples ("Team Alpha" crew name, "tesekkur" — missing diacritics on "təşəkkür") localized/fixed across `az.json`/`ru.json`/`en.json`.
- Sidebar navigation: every one of the 9 primary sections now has a small inline icon (matching the app's existing hand-drawn line-icon style, no new icon-library dependency) plus a left accent bar and softer highlight on the active item, replacing the flat text-only list.

### Verification
Full backend suite (528/528 passing, unchanged since only `seed.py`'s literal string changed), frontend `tsc --noEmit` clean, frontend production build clean (all 42 routes). A locale-file audit (every key in `az.json`/`ru.json`/`en.json` read end-to-end) found no remaining "Lead"/"CRM"/"Demo"/"Sample"/"Lorem ipsum"/"Dummy"/"Test" wording, and a repo-wide grep for the same terms plus `TODO`/`FIXME`/"Coming soon" across `frontend/app` and `frontend/components` came back clean.

## [2.13.0] — 2026-07-09 — The Complete Project Workflow

Turns the Project workspace into the full operational workflow G-STONE GALLERY runs a job through, end to end. Entirely inside the existing Sales module — no new module, no new nav entries.

### Added
- Project workspace expanded from 8 to 10 tabs, reordered to: Ümumi, Məkanlar, **Məmulatlar**, **Materiallar**, Ölçülər, Çertyojlar, Fotolar, İstehsal, Quraşdırma, **Təhvil**.
- "Məmulatlar" tab: a flat, project-wide table of every piece across every Room (room, type, stone, quantity, notes).
- "Materiallar" tab: pieces grouped by exact Stone + Thickness + Size combination, with item count and total quantity per group.
- `ProjectItem.completion_status` (new nullable column: `pending`/`delivered`/`accepted`) — "Təhvil" (handover to the customer) tracked per physical piece, distinct from `production_status`/`installation_status`.
- Two new Project Item types: `fireplace` (Kamin), `window_sill` (Pəncərə altlığı).
- Four new Room types: `corridor` (Dəhliz), `balcony` (Eyvan), `facade` (Fasad), `yard` (Həyət).
- 6 new backend tests.

### Changed
- "Təhvil" tab rebuilt from four static stat cards into a per-item editable status table (same pattern as the existing Production/Installation tabs), plus a small summary row.
- The curated "Məmulat" type picker now matches Sprint 5's authoritative 12-item list exactly (both `vanity` and `bathroom_furniture` offered together; `sink` no longer offered but stays valid for Items saved before this sprint).
- The curated "Məkan" type picker now matches Sprint 5's authoritative 8-item list (`staircase`/`exterior` no longer offered but stay valid for Rooms saved before this sprint — staircase work is now modeled as an `ITEM_TYPE_STAIRS` piece within any Room).

### Verification
Full backend suite (528/528 passing — 522 prior + 6 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes).

## [2.12.0] — 2026-07-09 — Production-Ready Material Selector

Normalizes the Brand → Stone → Thickness → Size flow: a Stone can now offer several thickness and size options instead of one free-text pair baked into the Material row, and every Project Item records exactly which option it was built with. Entirely inside the existing Catalog/Sales modules — no new module.

### Added
- `MaterialThickness`/`MaterialSize` (`catalog_material_thicknesses`/`catalog_material_sizes`): normalized option lists per Stone, full CRUD (add/list/delete), same sub-resource pattern as `MaterialImage`/`MaterialDocument`.
- `ProjectItem.material_thickness_id`/`material_size_id`: nullable FKs recording the specific option chosen for that item.
- Material detail page: "Thickness Options"/"Size Options" cards (list + add + delete), with `<datalist>` suggestions repurposed from Sprint 2's now-unused `SUGGESTED_THICKNESSES_MM`/`SUGGESTED_SIZES_MM`.
- Project workspace's "Add Item" form: Brand → **searchable** Stone (debounced server-side search) → Thickness → Size, the latter two populated from the selected Stone's own options.
- `SUPPORTED_BRANDS` curated suggestion list (NEOLITH, MARAZZI THE TOP, SAPIENSTONE, INALCO, ANATOLIA, BELENCO, COANTE) as `<datalist>` suggestions on the Brand creation form — `Brand.name` stays free text, no manufacturer specs stored.
- 8 new backend tests: Thickness/Size CRUD, per-material scoping, audit logging, and `ProjectItem` thickness/size selection.

### Changed
- Material creation form no longer collects thickness/dimensions at Stone-creation time — those are now added afterward via the detail page's new option cards. The legacy `thickness_mm`/`dimensions` columns on `StoneMaterial` are untouched (backward compatible with existing Materials).
- Migration adds `sales_project_items`' two new FK columns via a SQLite-safe `batch_alter_table` (SQLite can't `ALTER TABLE ADD CONSTRAINT` directly; verified with a full upgrade/downgrade/upgrade round-trip).

### Verification
Full backend suite (522/522 passing — 514 prior + 8 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes).

## [2.11.0] — 2026-07-09 — Measurement & Room Management

Makes "Layihə" (Project) genuinely the primary business object: a Project now contains Rooms, each Room contains Project Items (the physical pieces being fabricated), and each Project Item owns its Material, Measurement history, Drawings, and Photos. Built entirely inside the existing Sales module (no new module) — an initial plan to build Measurement/Room as standalone modules was corrected mid-sprint to avoid duplicating the Project/Quote structure that already exists there.

### Added
- **`Room`** (`sales_rooms`): kitchen/bathroom/living_room/staircase/exterior/custom, scoped to a Project, with an optional custom label.
- **`ProjectItem`** (`sales_project_items`): the curated piece vocabulary from Sprint 2 (countertop, island, sink *(new)*, tv_panel, vanity, wall_cladding, flooring, stairs, table, other), scoped to a Room, with a Brand→Stone→Thickness→Size Material reference (never free text), quantity, production status, and installation status.
- **`ProjectItemMeasurement`** (`sales_project_item_measurements`): every recorded measurement is a new revision (never an overwrite) — length/width/thickness, computed area, measurer name, measurement date, notes, and an attachable customer signature.
- **`ProjectItemDrawing`** / **`ProjectItemPhoto`**: DWG/DXF/sketch/PDF drawings and site photos attached to a Project Item, backed by the existing core `documents` store (same pattern as Catalog's material documents/images).
- New Sales API endpoints for all of the above (`/sales/projects/{id}/rooms`, `/sales/rooms/{id}/items`, `/sales/project-items/{id}/measurements`, `.../drawings`, `.../photos`) — all gated by the existing `sales:projects:read`/`write` permissions, no new permission strings.
- Project detail page rebuilt into a tabbed workspace: Overview, Rooms, Measurements, Drawings, Photos, Production, Installation, Completion.
- 22 new backend tests (`tests/sales/test_rooms_and_project_items.py`): CRUD, revisioning, cross-tenant isolation, audit log + domain event coverage for every write action.

### Changed
- `core/storage/router.py`'s upload allowlist extended to accept DWG/DXF files (by MIME type or, for the common `application/octet-stream` browser fallback, by filename extension) — required for the Drawings tab.

### Verification
Full backend suite (514/514 passing — 492 prior + 22 new), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes).

## [2.10.0] — 2026-07-09 — G-STONE Sprint 2: Simplified Navigation & Layihə-Centric Workflow

A usability restructuring driven by real G-STONE office feedback that the app read like accounting software rather than a gallery workflow tool. Re-anchors the UI around "Layihə" (Project) and its pieces, and pushes 1C's territory (warehouse/stock/accounting) out of daily view. No backend schema changes; nothing was deleted, only regrouped.

### Changed
- **Primary sidebar reduced from ~20 flat entries to 9 module-level sections**: İdarə Paneli, Müştərilər, Layihələr, Materiallar, İstehsal, Quraşdırma, Mesajlar, Hesabatlar, Ayarlar — the "module-level primary nav, secondary nav within a module" structure `UI_UX_GUIDELINES.md` §6.1 always called for. Everything that used to have its own sidebar entry is still reachable, either via a new `SectionTabs` in-page tab bar (`components/ui/section-tabs.tsx`) on the CRM, Catalog, and Sales/Orders pages, or from the new `/settings` hub below.
- **New `/settings` hub page** groups back-office pages that don't belong in daily use: Channels/Templates/Integrations (messaging admin), Warehouses/Slabs/Price Lists (Catalog admin), and Orders/Invoices/Expenses/AI Assistant (oversight convenience links). Uses the `settings.*Desc` translation keys added in a prior session but never wired to a page until now.
- **`nav.catalog` renamed** from "Daş Kataloqu" / "Каталог камня" / "Stone Catalog" to "Materiallar" / "Материалы" / "Materials" in all three locale files — plainer office terminology.
- **Material creation form** (`catalog/materials/new`): `thickness`/`dimensions` changed from free-text inputs to curated dropdowns (common slab thicknesses/sizes) with a manual "Other" fallback, presenting entry as a Brand → Stone → Thickness → Size cascade ahead of a future supplier-catalog import. No manufacturer spec data was hardcoded — only everyday defaults.

### Added
- **Seven new Sales `item_type` values** — `countertop`, `island`, `tv_panel`, `bathroom_furniture`, `flooring`, `stairs`, `table` (Mətbəx dəzgahı, Ada, TV paneli, Hamam mebeli, Döşəmə, Pilləkən, Masa) — added to `VALID_ITEM_TYPES` / `MATERIAL_ITEM_TYPES` / `ITEM_TYPE_DEFAULT_UNIT` in `modules/sales/domain/value_objects.py`. Each new type is a physical piece, not a billing-only line, and rides on the existing per-item `material_id`/`production_status`/`installation_status` fields `OrderItem`/`QuoteSectionItem` already had — only the controlled vocabulary grew, no migration needed.
- Translated labels for every item type (`sales.itemType_*`, all 19 values, in all three locale files) — fixes a pre-existing i18n gap where the Quote builder and Order detail pages rendered the raw English slug (e.g. `wall_cladding`) verbatim instead of a translated label.

### Fixed
- `crm.title`/`crm.subtitle` keys were present in `ru.json` but missing from `az.json`/`en.json` (a partial addition left over from a prior session); added for parity.

### Verification
Full backend suite (492/492 passing), frontend `tsc --noEmit` clean, frontend production build clean (all 38 routes, including the new `/settings` route).

## [2.9.3] — 2026-07-08 — Production Readiness follow-up: i18n, dark mode, breadcrumbs

A second pass over the four Phase 3 research findings that landed after 2.9.2 was already committed: an i18n audit, a responsive/dark-mode audit, a navigation/breadcrumb audit, and a CRUD-completeness audit. No new features, no business-logic changes.

### Fixed
- **`az.json` had one untranslated string**: `catalog.tableDefault` was left as the literal English `"Default"` even though Azerbaijani is the app's default locale, so every AZ user saw raw English on the Price Lists table's "Default" column. Translated to `"Standart"`, consistent with the existing `"standart"` usage elsewhere in the same file.
- **Dashboard/Reports chart gridlines and data-point strokes were hardcoded to light-mode hex colors** (`components/ui/charts.tsx`): gridlines used a fixed `#E2E5EA` (the light theme's border color) and point strokes used a fixed `#FFFFFF`, so both were nearly invisible or wrong against a dark background. Switched both to the existing `--color-border`/`--color-surface` CSS custom properties, which already repoint automatically between light and dark (same mechanism every other themed element in the app uses) — verified live in a browser with the dark-mode toggle active.
- **Breadcrumb inconsistency across detail pages**, flagged as a known gap as far back as the 2.9.1 changelog entry: only the Customers detail page had real breadcrumbs; the other nine (Orders, Production, Catalog Materials, Catalog Price Lists, CRM Tasks, Finance Invoices, Installation Jobs, Sales Projects, and the Sales Quote builder) used a plain "← Back to X" link instead. Extracted a shared `Breadcrumb` component (`components/ui/breadcrumb.tsx`) from the Customers page's existing markup and applied it to all ten pages; the Quote builder now shows the full three-level trail (Projects / project name / quote number). Verified live for five of the ten pages with real records (the rest share the identical, type-checked pattern against empty tables in the current dev database).

### Removed
- Eight now-orphaned `backTo*`/`back` translation keys (`orders.backToOrders`, `production.backToWorkOrders`, `finance.backToInvoices`, `tasks.backToTasks`, `installation.backToInstallation`, `sales.backToProjects`, `sales.backToProject`, `catalog.materialDetail.back`) from all three locale files, left dead by the breadcrumb replacement above. `tasks.backToPending` (a different, still-used string) was left untouched.
- Two small pre-existing dev artifacts found while editing these same files: an unused `updateProject` import on the Sales Project detail page, and an unused `CardHeader` import left over from 2.9.2's Quote Settings panel.

### Corrected
- **Investigated and declined a finding from an earlier research pass**: CRM Customer archive was reported as missing a "Restore" button in the UI, with the assumption that the existing `PATCH /crm/customers/{id}` endpoint could already un-archive a customer. On inspection, `UpdateCustomerUseCase` never touches `deleted_at` — only `ArchiveCustomerUseCase` does, and no restore use case exists anywhere in the backend. Adding one would be new business logic, out of scope for this pass; recorded as a genuine, not-yet-built gap instead of a wiring fix.
- **Considered and declined adding a sidebar icon library.** `UI_UX_GUIDELINES.md` calls for one consistent icon set across all ~20 nav items; the sidebar has been text-only since day one. This is a real design-system decision (icon set choice, sizing, every nav entry and page header touched) rather than a bug fix, so it was left as a documented, deliberately deferred gap rather than partially addressed.

### Verification
Full backend suite (492/492 passing, unchanged from 2.9.2 since no backend files were touched), frontend `tsc --noEmit` clean, frontend production build clean (all 41 routes), and a live end-to-end Playwright smoke test against the real dev database and both running servers: login, company selection, every touched list page, and five of the ten breadcrumb-refactored detail pages (Customers, Sales Projects, CRM Tasks, Catalog Price Lists, and the Sales Quote builder) exercised with real records and zero console errors; dark mode toggled live and the chart color fix confirmed via computed style (gridline stroke resolves to the dark theme's border color, not the old hardcoded light hex).

## [2.9.2] — 2026-07-08 — Production Readiness & G-STONE Onboarding

Phase 3: a full application-perspective audit ahead of real daily use by G-STONE GALLERY — every navigation item, CRUD flow, filter/sort/export, permission path, company switch, responsive/dark-mode/i18n behavior, and loading/empty/error state reviewed. Four independent research passes (backend security/demo-data, frontend branding/demo-data, navigation/i18n/UX-states, CRUD/filters/permissions/company-switching) plus a live end-to-end Playwright smoke test against the real dev database. No new features, no business-logic changes. See `PRODUCTION_READINESS_REPORT.md` for the full audit findings, including items considered and deliberately deferred.

### Fixed
- **Sales → Projects "create project" form was completely broken**: `listCustomers({ limit: 200 })` requested more rows than the `GET /crm/customers` endpoint allows (`le=100`), so every load of the customer dropdown 400'd and the picker silently rendered empty — Create was unusable from that form. Capped the request at 100.
- **Orders list `sort` parameter was accepted but silently ignored**: the API and frontend wrapper both had a `sort` field, but `OrderRepository.list()` always ordered by `created_at desc` regardless of its value. Wired it to a real `_SORTABLE` field map (`order_number`, `status`, `created_at`, `total_final`), matching the pattern already used by `ProjectRepository`.
- **Sales Quotes had no way to edit VAT rate, discount, currency, validity date, or notes after creation** — the backend `PATCH /quotes/{id}` endpoint and its translation keys existed but nothing in the UI called it, so every quote was stuck with its creation-time defaults. Added an editable "Quote Settings" panel to the quote builder page, active while a quote is in `draft`.
- **Frontend `Quote.discount_type` TypeScript type didn't match the backend**: declared `"percentage"` where the backend only recognizes `"percent"` (`totals.py`). Dormant only because no UI ever set the field; would have silently produced a zero discount the moment the new settings panel started sending it. Fixed the type and used the correct value.
- **Catalog Brands and Warehouses had no archive/restore affordance**: `PATCH .../status` existed and worked (Materials already used it), but the Brands/Warehouses list pages never exposed it. Added an Active/Hidden toggle button per row, and both lists now include hidden entities so a restore path exists.
- Missing favicon — added `frontend/app/icon.svg` (Next.js's file-based icon convention), a simple "G" monogram in the app's primary color. Browser tabs previously showed a generic/blank icon.
- Browser tab title was the same static "G-STONE ERP" on every one of the ~30 routes. `AppShell` now sets `document.title` to the active section's translated nav label on every in-app (client-side) navigation. Known remaining limitation: because the entire `(app)` route group is client-rendered behind a token-check gate (no per-route `generateMetadata` is possible without restructuring every page to a server-component wrapper), a hard page reload or a directly-opened/bookmarked URL still shows the static app-wide title until the next in-app navigation — documented as a follow-up rather than fixed here.

### Changed
- Sales Projects list gained the status filter and sortable-column headers every sibling list page already had (backend already supported both `status` and `sort` query params; the frontend simply never wired them up).
- Removed two dead, unused translation keys (`sales.serviceSettings` / `sales.servicePriceUpdated`, orphaned from an earlier abandoned feature) from all three locale files and repurposed the slots for the new Quote Settings UI strings (`quoteSettings`, `discountTypeNone/Percent/Fixed`, `discountValue`) — key parity across `en.json`/`az.json`/`ru.json` maintained.

### Verification
Full backend suite (492/492 passing), frontend `tsc --noEmit` clean, frontend production build clean (all 41 routes), and a live end-to-end Playwright smoke test against the real dev database and both running servers: login, company selection, every touched page loaded with zero console/HTTP errors, a real brand created and its archive/restore toggle exercised, and a real project → quote created with its new Quote Settings panel edited and confirmed persisted across a page reload.

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
