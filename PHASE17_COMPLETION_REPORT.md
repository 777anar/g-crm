# Phase 17 Completion Report — Stabilization & Technical Debt Closeout

_Date: 2026-07-22_
_Version: 2.36.0_
_Scope: every item in `MASTER_DEVELOPMENT_ROADMAP.md`'s Phase 17, in full. No new modules, no schema redesign, no business-logic changes — this is a technical-debt closeout, not a feature release._

---

## 1. Why This Phase Exists

`MASTER_DEVELOPMENT_ROADMAP.md` opens Part 3 (remaining work) with Phase 17 for a specific, named reason: every one of its eight items had already been independently re-identified across two or more prior audit passes — `RELEASE_CHECKLIST.md` (2026-06-30/2026-07-08), `PROJECT_AUDIT.md` (2026-07-21), and `IMPLEMENTATION_REPORT.md` (2026-07-22) — without ever being picked up. Each re-identification is cited by ID (B1, B5, B6, B7, S5) or by name in the source documents. This phase closes all eight in one pass specifically so none of them appear as "still open" in a ninth audit.

Every item below was implemented, tested, and verified — not partially addressed and not deferred.

---

## 2. Items Closed

### 2.1 Customer archive restore path (B6)

**Problem:** `UpdateCustomerUseCase` never touched `deleted_at`; no restore use case, endpoint, or repository method existed anywhere in `modules/crm`. Archiving a customer was a one-way door. First named in `RELEASE_CHECKLIST.md` (2026-07-08), re-confirmed still open in `PROJECT_AUDIT.md` and `IMPLEMENTATION_REPORT.md` §8 (B6).

**Fix:**
- `RestoreCustomerUseCase` (`backend/modules/crm/application/use_cases/customer_use_cases.py`) — mirrors `ArchiveCustomerUseCase` exactly: validates the customer exists and is currently archived, clears `deleted_at`, records an audit entry (`customer.restored`), publishes a new `CustomerRestored` domain event.
- New `CustomerNotArchivedError` domain exception, `RestoreCustomerInput` DTO, `CUSTOMER_RESTORED` event constant.
- `POST /api/v1/crm/customers/{id}/restore` (`backend/modules/crm/presentation/api/customers.py`), gated by the existing `crm:customers:write` permission (same tier as archive) — `409 CONFLICT` if the customer isn't archived, `404` if it doesn't exist.
- Frontend: `restoreCustomer()` added to `lib/api/crm.ts`. The Customer detail page (`app/(app)/crm/customers/[id]/page.tsx`) shows a "Restore" button in place of "Archive" once a customer is archived. The Customers list page (`app/(app)/crm/customers/page.tsx`) gained a per-row quick-restore action in the archived-status column, visible only when viewing archived customers.
- New translation keys (`restoreCustomer`, `restoring`, `restoreConfirm`, `restoreFailed`, `restored`) added to both the `customerProfile` and `customers` locale namespaces across `az.json`/`ru.json`/`en.json`.

**Tests:** 5 new (`tests/crm/test_customers_api.py`) — successful restore, restore-when-not-archived returns `409`, restore-nonexistent returns `404`, restore requires write permission (`403` for a viewer), and a dedicated audit-log verification test.

### 2.2 Finance invoice / Production work-order list `sort` parameters (B1)

**Problem:** `InvoiceRepository.list()` and `WorkOrderRepository.list()` accepted no `sort` argument at all, unlike every sibling list endpoint (Orders, Customers, Leads, etc.), which all follow the same whitelisted-column `?sort=field`/`?sort=-field` convention. Named in `PROJECT_AUDIT.md` as B1, re-confirmed still open in `IMPLEMENTATION_REPORT.md` §8.

**Fix:**
- `InvoiceRepository.list()` gained a `_SORTABLE` map (`invoice_number`, `status`, `created_at`, `due_date`, `total_amount`) and a `sort` kwarg, exactly matching `OrderRepository.list()`'s established pattern (whitelisted columns, `-field` for descending, unknown values fall back to `-created_at`).
- `WorkOrderRepository.list()` gained the same treatment (`work_order_number`, `status`, `created_at`, `priority`, `scheduled_start_date`, `scheduled_completion_date`).
- Both `GET /api/v1/finance/invoices` and `GET /api/v1/production` gained a `sort` query parameter, passed straight through to the repository.
- Frontend: both list pages gained `SortableHeader` columns. Finance Invoices' sortable headers integrate with the existing column-resize toolkit (`width`/`resizeHandle` props); sort state is now also persisted through the page's saved-filter presets. Production's list page gained plain `SortableHeader` columns (it has no resize toolkit).

**Tests:** 4 new — 2 in `tests/finance/test_invoices.py` (ascending/descending sort by `invoice_number`, and an unwhitelisted-column value falling back cleanly rather than erroring), 2 in `tests/production/test_work_orders.py` (ascending/descending by `work_order_number`, and sorting by `priority`).

### 2.3 Committed, CI-enforced ESLint configuration

**Problem:** No `.eslintrc*`/`eslint.config.*` existed anywhere in `frontend/`. `npm run lint` was documented as a standard command in `CLAUDE.md` but simply had nothing to run against — `next lint` would hang waiting for interactive setup. `tsc --noEmit` was the only enforced static check. Named in `PROJECT_AUDIT.md` §7 and Priority List item 7.

**Fix:**
- Added `eslint@^9`, `eslint-config-next@15.5.19` (pinned to match the installed Next.js version exactly), and `@eslint/eslintrc` (needed to bridge the legacy `next/core-web-vitals` shareable config into ESLint 9's flat-config format) as devDependencies.
- New `frontend/eslint.config.mjs`: a flat config extending `next/core-web-vitals` and `next/typescript` via `FlatCompat`.
- New `Lint` step added to `.github/workflows/ci.yml`'s frontend job, between `Type check` and `Production build` — a lint violation now fails CI, not just a local run someone remembers to do.

**What running it for the first time surfaced, and how each category was handled** (see §3 below for the full breakdown — nothing was suppressed via a rule downgrade or a blanket `eslint-disable`):
- 89 `@typescript-eslint/no-explicit-any` violations, all the identical pattern (`t(dynamicKey as any)`, a cast needed to satisfy `next-intl`'s literal-keyed `t()` signature against a runtime-computed translation key) — mechanically replaced with the type-scoped `as Parameters<typeof t>[0]` equivalent across 36 files. Same runtime behavior; verified with `tsc --noEmit` after.
- 4 genuine free-form-JSON `any` usages (`AIRecommendation.response`/`edited_response` in `lib/types.ts`, `reviewRecommendation`'s `editedResponse` parameter in `lib/api/ai.ts`) — retyped `Record<string, unknown>`.
- 6 dead imports/variables (`useCallback` and an unused `toast` in Cut Optimization's tool page; unused `tCommon` in Production Stages; unused `CardHeader` import in Sales Projects; unused `REPORT_PERIODS` import in the shared date-range filter; a stale `eslint-disable-next-line react-hooks/exhaustive-deps` with nothing left to suppress; a fully dead `currentUserId` state variable in the Communication Inbox, set from `me()` and never read) — all removed.
- 1 `jsx-a11y/role-supports-aria-props` finding on `SortableHeader` — `aria-sort` was set on the inner `<button>`, which the ARIA spec doesn't support; moved to the enclosing `<th>`, the correct target.

**Verification:** `npm run lint` exits with zero errors and zero warnings. `npm run build`'s own internal lint pass (Next.js runs ESLint as part of `next build`) also passes clean.

### 2.4 Dead frontend data: `module_permissions` (B7)

**Problem:** `me()` fetched `module_permissions` from the auth API on every session; nothing in the frontend ever consumed it. Named in `PROJECT_AUDIT.md` as B7.

**Fix — wired up, not removed** (the roadmap explicitly framed this as "remove or wire it to a permission-gating hook"; wiring it up was chosen since the data is exactly what the long-deferred permission-gating feature (S5 in every prior audit) needs):
- New `frontend/lib/permissions.ts`: `hasPermission(permission: string): boolean` decodes the current access token's `role`/`module_permissions` claims (the same claims `core/rbac/dependencies.py` decodes and enforces server-side) and replicates `core/rbac/permissions.py`'s role-rank + action-suffix convention (`read`→viewer, `write`→rep, `approve`→manager, `settings:read`→manager, `settings:write`→owner) client-side, including the per-user `module_permissions` override check.
- `usePermission(permission: string): boolean` — a React hook wrapping `hasPermission()`, mount-only (renders `false` during SSR/first paint, resolves to the real value post-mount), matching this codebase's established SSR-safe hydration pattern (`useLocalStorageState`, `useUrlFilters`).
- Applied as the demonstrated pattern (this codebase's established practice for a new shared primitive — see e.g. `Toast` first landing on the Leads page before rolling out platform-wide) to the Customers list (Create button, the bulk-action bar and its selection checkboxes, the per-row Restore action) and the Customer detail page (Archive/Restore button) — closing the exact "a viewer sees the same Create/Edit/Archive buttons as an owner" gap `PROJECT_AUDIT.md` named.
- Explicitly **not** a security boundary of its own: every gated action's underlying endpoint still enforces `require_permission` independently. This is a UX affordance, and is described as such in the code's own docstrings.

**Scope note:** platform-wide rollout to every write control across every list/detail page was **not** done in this pass — that would be a much larger, separate UI initiative, and the roadmap's own Phase 17 sizing (`Size: S`) and this project's own precedent (new shared UI primitives ship on one demonstrated surface first) both point the same way. This is recorded as a real, intentional scope boundary, not a gap discovered after the fact.

### 2.5 Circular FK cleanup (B5)

**Problem:** `crm_customers.primary_contact_id` → `crm_contacts.id` and `crm_contacts.customer_id` → `crm_customers.id` form a mutual foreign-key reference. `Base.metadata.sorted_tables` (used by `create_all()` and Alembic's autogenerate table-sort) raised a live `SAWarning`: *"Cannot correctly sort tables; there are unresolvable cycles between tables 'crm_contacts, crm_customers'... this warning may raise an error in a future release."* Named as B5 in `PROJECT_AUDIT.md`.

**Fix:**
- `Customer.primary_contact_id`'s `ForeignKey` gained `use_alter=True, name="fk_crm_customers_primary_contact_id"` (`backend/modules/crm/infrastructure/models/customer.py`) — the standard SQLAlchemy resolution for a circular FK: this specific constraint is now added via a post-`CREATE TABLE` `ALTER TABLE` rather than requiring both tables to exist simultaneously at creation time, which is what breaks the cycle for table-sort purposes.
- **Confirmed via `alembic check` that no migration was required** — the change is purely at the SQLAlchemy metadata level; the already-migrated database's actual constraint is unaffected. This was verified directly (`alembic check` reported "No new upgrade operations detected") rather than assumed.
- Reproduced the exact warning before the fix and confirmed it no longer fires after, using a script that imports every installed module's models (the same set `tests/conftest.py` imports) and calls `Base.metadata.sorted_tables`.

**Tests:** 2 new (`backend/tests/test_database_schema.py`, new file) — one asserts `Base.metadata.sorted_tables` raises no "unresolvable cycles" warning across the full 14-module table set (guards against a *future* circular FK being introduced elsewhere, not just this one), one pins down that `Customer.primary_contact_id`'s FK specifically has `use_alter=True` and the expected constraint name (so a future refactor that accidentally drops `use_alter` fails with a clear, specific message rather than just the generic warning check).

### 2.6 Tablet breakpoint fix

**Problem:** `UI_UX_GUIDELINES.md` §7 specifies an icon-only collapsed sidebar at the tablet breakpoint (768–1023px); the app instead gave tablets the same full slide-over drawer as phone widths. Named in `PROJECT_AUDIT.md` §7 and reconfirmed in multiple audit passes.

**Fix:**
- New `NavIconRail` component (`frontend/components/app-shell.tsx`) — a persistent (no open/close state, unlike the drawer), icon-only sidebar rendering the same `NAV_ITEMS` as the full sidebar, each entry's label available via `title`/`aria-label` since there's no visible text at this width.
- `AppShell` now has three responsive tiers instead of two: `<md` (phone, <768px) gets the slide-over drawer via a hamburger button (now `md:hidden` instead of `lg:hidden`); `md` to `<lg` (tablet, 768–1023px) gets the new persistent `NavIconRail` (`hidden md:block lg:hidden`); `>=lg` (desktop, 1024px+) keeps the existing full labeled sidebar, unchanged.
- The mobile drawer's outer wrapper is also now `md:hidden` (was `lg:hidden`), so it can never render at tablet width even if triggered.

### 2.7 Mobile nav focus trap

**Problem:** The mobile slide-over drawer's Escape-to-close and backdrop-click-to-close both worked, but keyboard `Tab` could escape the open drawer into the page content behind it. Named in `PROJECT_AUDIT.md` §7.

**Fix:**
- New `useFocusTrap(containerRef, active)` hook (`frontend/lib/use-outside-click.ts`, alongside the existing `useOutsideClick`/`useCloseOnEscape`): while `active`, moves focus to the first focusable element inside the container on activation, intercepts `Tab`/`Shift+Tab` to cycle focus within the container's focusable elements (wrapping from last back to first and vice versa), and restores focus to whatever was focused before (the hamburger button) on deactivation.
- Wired into `AppShell`'s mobile drawer via a new `mobileNavRef`, active exactly while `mobileNavOpen` is true.

### 2.8 Icon library decision

**Problem:** 8+ components hand-rolled inline `<svg>` icons, an explicit, named deviation from `UI_UX_GUIDELINES.md` §2's "a single consistent icon library (e.g., Lucide) used everywhere" — code comments in the codebase explicitly framed this as "avoiding a real design-system decision," deferred across multiple prior sessions.

**Fix — the decision was made: Lucide.**
- Added `lucide-react` as a dependency (zero transitive dependencies, tree-shakeable, and the exact library `UI_UX_GUIDELINES.md` itself names as the example).
- Replaced every hand-rolled inline SVG icon found (9 icons across 6 files, confirmed by a full `<svg` grep across `app/` and `components/` before and after):
  - `app-shell.tsx`: the hamburger menu icon (`Menu`), the drawer close icon (`X`), and all 6 primary-nav section icons (`LayoutDashboard`, `TrendingUp`, `Package`, `CircleDollarSign`, `BarChart3`, `Settings`) — the same icon set now powers both the full sidebar and the new tablet `NavIconRail`.
  - `theme-toggle.tsx`: sun/moon (`Sun`/`Moon`).
  - `company-switcher.tsx` and `language-switcher.tsx`: the dropdown chevron (`ChevronDown`), identical in both.
  - `quick-create-menu.tsx`: the plus icon (`Plus`).
  - `ui/data-table.tsx`: the column-visibility icon (`Columns3`).
- Same visual sizing, stroke width, and `aria-hidden` conventions preserved at every call site — this is a like-for-like icon swap, not a redesign.
- Remaining `<svg>` usage in the codebase (charts, the Cut Optimization slab-layout diagram, the Offcut Library's placeholder graphic, `Button`'s loading spinner) is genuine data-visualization/illustration content, not iconography, and was correctly left untouched.

---

## 3. Files Changed

| Area | Files |
|---|---|
| Backend — CRM | `domain/events.py`, `domain/exceptions.py`, `application/dtos.py`, `application/use_cases/customer_use_cases.py`, `application/use_cases/__init__.py`, `presentation/api/customers.py` |
| Backend — Finance | `infrastructure/repositories/invoice_repository.py`, `presentation/api/invoices.py` |
| Backend — Production | `infrastructure/repositories/work_order_repository.py`, `presentation/api/work_orders.py` |
| Backend — Catalog/CRM schema | `modules/crm/infrastructure/models/customer.py` |
| Backend — tests | `tests/crm/test_customers_api.py`, `tests/finance/test_invoices.py`, `tests/production/test_work_orders.py`, `tests/test_database_schema.py` (new) |
| Frontend — new files | `lib/permissions.ts`, `eslint.config.mjs` |
| Frontend — CRM | `app/(app)/crm/customers/page.tsx`, `app/(app)/crm/customers/[id]/page.tsx`, `lib/api/crm.ts` |
| Frontend — Finance/Production | `app/(app)/finance/invoices/page.tsx`, `app/(app)/production/page.tsx`, `lib/api/finance.ts`, `lib/api/production.ts` |
| Frontend — navigation/a11y | `components/app-shell.tsx`, `lib/use-outside-click.ts`, `components/ui/sortable-header.tsx` |
| Frontend — icons | `components/app-shell.tsx`, `components/theme-toggle.tsx`, `components/company-switcher.tsx`, `components/language-switcher.tsx`, `components/quick-create-menu.tsx`, `components/ui/data-table.tsx` |
| Frontend — lint fixes | 36 files with `as any` → `as Parameters<typeof t>[0]`; `lib/types.ts`, `lib/api/ai.ts` (`Record<string, unknown>`); `app/(app)/cut-optimization/page.tsx`, `app/(app)/production/stages/page.tsx`, `app/(app)/sales/projects/page.tsx`, `components/date-range-filter.tsx`, `lib/use-local-storage-state.ts`, `app/(app)/communication/inbox/page.tsx` (dead code removal) |
| Frontend — i18n | `locales/az.json`, `locales/ru.json`, `locales/en.json` |
| Tooling | `frontend/package.json`, `frontend/package-lock.json` (`lucide-react`, `eslint`, `eslint-config-next`, `@eslint/eslintrc`), `.github/workflows/ci.yml` |
| Docs | `CHANGELOG.md`, `ROADMAP.md`, `IMPLEMENTATION_REPORT.md`, `MASTER_DEVELOPMENT_ROADMAP.md` |

No database migration was added or required (see §2.5).

---

## 4. Tests Added

**11 new backend tests: 695 → 706 passing.**

| File | New tests | What they cover |
|---|---|---|
| `tests/crm/test_customers_api.py` | 5 | Restore success, restore-when-not-archived (409), restore-nonexistent (404), restore requires write permission (403), audit-log entry recorded |
| `tests/finance/test_invoices.py` | 2 | Sort ascending/descending by `invoice_number`, unwhitelisted sort column falls back cleanly |
| `tests/production/test_work_orders.py` | 2 | Sort ascending/descending by `work_order_number`, sort by `priority` |
| `tests/test_database_schema.py` (new) | 2 | No circular-FK `SAWarning` across the full schema, `use_alter`/constraint name pinned on `Customer.primary_contact_id` |

No frontend unit-test framework exists in this codebase (Playwright e2e only — one smoke spec, per this project's established testing profile). Frontend changes were verified via `tsc --noEmit`, `npm run lint`, and a full production build, consistent with how every other frontend-only change in this project's history (e.g. Version 2.8.1, 2.18.0–2.21.0) has been verified.

---

## 5. Verification

| Check | Result |
|---|---|
| Backend test suite | **706/706 passing** (695 prior + 11 new) |
| `lint-imports` (core/module architecture boundary) | **Passing** — 1 contract kept, 0 broken |
| `alembic check` | **Clean** — no migration required |
| Frontend `tsc --noEmit` | **Clean** |
| Frontend `npm run lint` | **Clean — 0 errors, 0 warnings** |
| Frontend production build | **Clean — 68 routes**, unchanged route count (no new pages; this is a stabilization pass) |

All six checks were run after every implementation item, not just once at the end — several genuine mistakes were caught and fixed this way during implementation (a `scheduled_start_date`/`scheduled_completion_date` sortable-column mismatch against what the Production list page actually displays; a `setCurrentUserId` reference in the Communication Inbox left dangling after an initial, incorrect assessment that the corresponding state was fully dead code).

---

## 6. What Was Deliberately Not Done (and Why)

- **Platform-wide frontend permission gating** — `hasPermission()`/`usePermission()` exists and is demonstrated on one surface (Customers). Rolling it out to every write control on every page is a materially larger UI initiative, correctly out of scope for a `Size: S` stabilization phase per `MASTER_DEVELOPMENT_ROADMAP.md`'s own sizing.
- **CORS tightening, httpOnly-cookie token migration, Postgres RLS** — all real, all named in prior audits, all deliberately scoped to `MASTER_DEVELOPMENT_ROADMAP.md` Phase 18 (Security & Compliance Hardening), not Phase 17. Mixing security-boundary changes into a "no business-logic changes" stabilization pass would have been scope creep against this phase's own stated theme.
- **Mobile client** — explicitly Phase 25 in the master roadmap; untouched here, as expected.
- **A dedicated `usePermission()` rollout audit across all ~24 list pages** — not attempted; the roadmap's Phase 17 item was "wire it up," not "gate everything," and the completion criteria above reflect that literally.

---

## 7. Summary

All eight Phase 17 items are closed, verified, and documented. The backend suite grew by 11 tests with zero regressions; the frontend went from zero enforced lint coverage to a clean, CI-gated `eslint` pass with 93 genuine pre-existing issues fixed (not suppressed); a live SQLAlchemy warning was resolved with no database migration; and three real, user-facing UX/accessibility gaps (customer restore, tablet navigation, keyboard focus trapping) were closed. Nothing in `PROJECT_ANALYSIS.md`'s frozen architecture changed, no module boundary was crossed, and no existing API contract was broken — confirmed by the full verification matrix in §5.

`MASTER_DEVELOPMENT_ROADMAP.md` has been updated to move Phase 17 from Part 3 (remaining work) to Part 2 (completed), with Phase 18 (Security & Compliance Hardening) now next.
