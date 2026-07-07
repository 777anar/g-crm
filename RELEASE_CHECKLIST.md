# G-STONE ERP — Release Candidate Checklist

_Date: 2026-06-30_
_Scope: full-application review (backend `backend/`, frontend `frontend/`) ahead of Release Candidate. No new modules or features were added during this pass — Critical and High findings were fixed in place; Medium/Low findings are documented for a future pass._

Each issue is classified **Critical / High / Medium / Low** and tagged with its category. Fixed items are marked **[FIXED]**.

---

## Critical

### C1. Path traversal in document upload — arbitrary file write **[FIXED]**
**Category:** Security
**Where:** `backend/core/storage/client.py` (`new_storage_key`), `backend/core/storage/router.py` (`upload_document`)

`new_storage_key()` interpolated the client-supplied `file.filename` directly into the storage key (`f"{company_id}/{module}/{uuid}-{filename}"`), which `LocalDiskStorageClient.upload()` then joined onto the base storage directory with `os.path.join` and `os.makedirs(os.path.dirname(path))`. A filename containing path segments (e.g. `../../../../etc/cron.d/evil`) would write outside the intended storage directory — a classic path-traversal / arbitrary file write, exploitable by any authenticated user via `POST /api/v1/core/documents`.

**Fix:** Sanitize the filename before it ever reaches a storage key — strip directory components (`os.path.basename`), strip any remaining `..`/leading dots, collapse to a safe character set, and cap length. Applied in `new_storage_key()` so every storage backend (local disk and the future Supabase client) gets the same guarantee.

### C2. Insecure default JWT secret with no production safeguard **[FIXED]**
**Category:** Security
**Where:** `backend/core/config.py`

`jwt_secret_key` defaults to the literal string `"dev-secret-change-me"`. Nothing in the application prevented booting in a non-development environment with this default still in place — if deployed as-is, every access/refresh token is forgeable by anyone who reads the (public) source code.

**Fix:** Added a startup guard in `create_app()`: if `settings.environment != "development"` and `jwt_secret_key` still equals the known default, the app refuses to start with a clear error. Development is unaffected.

---

## High

### H1. No rate limiting on the login endpoint **[FIXED]**
**Category:** Security
**Where:** `backend/core/auth/router.py`

`API_SPECIFICATION.md` §11 documents a 10 requests/minute/IP limit on `/api/v1/auth/login`, but no such limit was ever implemented (`RateLimitedError` existed in `core/api/errors.py` but was never raised anywhere). This leaves the login endpoint open to credential brute-forcing with no backend defense.

**Fix:** Added a minimal in-process fixed-window limiter (`core/rbac/rate_limit.py`, no new dependency) applied to `/api/v1/auth/login`: 10 attempts per IP per 60-second window, returning `429 RATE_LIMITED` past that. Documented as a Phase-1-appropriate implementation — a multi-instance deployment would need a shared store (Redis, already in the stack) instead of in-process state; noted in the code as the upgrade path.

### H2. No file size limit on uploads **[FIXED]**
**Category:** Security / Performance
**Where:** `backend/core/storage/router.py`

`upload_document` read the entire request body into memory (`await file.read()`) and wrote it to disk with no size check. Any authenticated user could exhaust server memory or disk with a single oversized upload.

**Fix:** Added a `MAX_UPLOAD_SIZE_BYTES` (10 MB) check against the read content length, returning a `VALIDATION_ERROR` (400) before the file is persisted.

### H3. Document upload has no RBAC enforcement (any authenticated user can upload) **[FIXED]**
**Category:** Security
**Where:** `backend/core/storage/router.py`

`upload_document` depended only on `get_current_user` (proves authentication) and never checked the caller's role tier, even though writing data is conventionally gated at `rep` tier and above per `core/rbac/permissions.py`'s action-suffix convention. A `viewer`-role user — explicitly meant to be read-only — could upload arbitrary documents to any entity in their company.

**Fix:** Changed the upload endpoint's dependency to `require_permission("core:documents:write")`, which resolves through the existing generic action-suffix tier check (`write` → minimum role `rep`) without needing to know which business module the upload is "for." The download endpoint (`get_document_url`) intentionally keeps the lower `get_current_user` bar, since `read` actions are already viewer-tier by the same convention.

### H4. Customer/Lead list pagination silently hides data past the page limit **[FIXED]**
**Category:** Performance / Data integrity
**Where:** `backend/modules/crm/presentation/api/customers.py`, `leads.py`; `frontend/app/(app)/dashboard/page.tsx`

`API_SPECIFICATION.md` documents cursor-based pagination (`next_cursor`), but both list endpoints hardcoded `next_cursor=None` regardless of whether more rows existed. Once a company passes the page-size cap (default 25, max 100), additional customers/leads become **silently invisible** — no error, no indication, no way to reach them via documented pagination. The Dashboard's stat counts (`limit: 100`) would also silently under-count past 100 records with no warning.

**Fix:** Implemented real offset-based cursor pagination: each list endpoint now queries one extra row past `limit`; if present, it returns a base64-encoded opaque cursor (`{"offset": N}`) instead of `null`. `CustomerRepository.list` / `LeadRepository.list` already accepted an `offset` parameter, so the repository layer needed no change. This is a minimal, correct fix consistent with the documented contract — not a new feature, since the API already promised this behavior. The frontend does not yet send `cursor` or render a "Load more" control; wiring that up is a UI feature addition and intentionally left out of this fix-only pass (tracked as a follow-up).

### H5. `assigned_manager_id` accepted without validating the referenced user **[FIXED]**
**Category:** Validation / Data integrity
**Where:** `backend/modules/crm/application/use_cases/customer_use_cases.py`

`CreateCustomerUseCase` and `UpdateCustomerUseCase` stored `assigned_manager_id` as given, with no check that the UUID refers to a real user — let alone a user who is actually a member of the active company. A typo'd or malicious UUID would be silently persisted, corrupting the "Assigned Manager" field with a dangling reference (and, if a UUID from another company's user happened to validate against a future cross-company lookup, a minor data-leak vector).

**Fix:** Both use-cases now verify `assigned_manager_id` (when provided) corresponds to a `UserCompanyRole` row for the active company before saving, raising `ValidationAPIError` (400) otherwise.

### H6. Customer Notes field has no accessible label **[FIXED]**
**Category:** Accessibility
**Where:** `frontend/app/(app)/crm/customers/[id]/page.tsx`

The persistent "Notes" textarea on the customer profile was rendered via `<TextAreaField label="" .../>`, producing an empty, unlabeled `<label>`. A screen reader user tabbing into this field hears no accessible name at all — a real WCAG 2.1 (4.1.2 Name, Role, Value) failure on a primary content-editing control, not a decorative one.

**Fix:** Gave it a real translated label (reusing `customerProfile.notes`, already in all three locale files) instead of an empty string.

---

## Medium

_Status as of the Version 2.9.1 "Enterprise Polish" pass (2026-07-07), which re-audited every item below against the current codebase — several were resolved incidentally by later versions (2.8.1, 2.9), the rest fixed directly in that pass._

| # | Issue | Category | Status |
|---|---|---|---|
| M1 | No upload content-type/extension allowlist | Security | **[FIXED in 2.9.1]** `core/storage/router.py` now checks `file.content_type` against an explicit allowlist (images, PDF, common office formats, plain text/CSV, and the audio/video types Communication Center's WhatsApp/Instagram/Messenger message attachments need) before accepting an upload, rejecting anything else with a clean `400`. |
| M2 | `customer.type` (individual/business) is now write-only dead weight | Tech debt | **Still deferred.** Unchanged from the original finding: fixing means either reintroducing a Type picker (a feature) or a migration to drop the column (riskier than warranted for a no-business-logic-change release) — both out of scope for a polish pass. |
| M3 | No toast/confirmation feedback on save actions | UX | **[FIXED]** Resolved incrementally: Version 2.8.1 introduced the global `Toast` primitive; Version 2.9.1 then found and fixed the actual remaining gap — several detail pages' write-action handlers (Orders/Production/Finance Invoice/Installation Job) had no error handling *at all*, not just no toast. All now report failures via `useToast`. |
| M4 | `CompanySwitcher` and `LanguageSwitcher` duplicate dropdown markup | Duplicate code | **[FIXED in 2.9.1]** Extracted into `components/ui/dropdown.tsx` (`useDropdown` hook + `DropdownPanel`/`DropdownItem` presentational components); both switchers now consume the shared primitive instead of hand-rolling their own open/close/panel/item markup. |
| M5 | Native `confirm()` used for customer archive | UX consistency | **[FIXED in 2.9.1]** New `components/ui/confirm-dialog.tsx` (`useConfirm()` + `ConfirmProvider`, mounted at the app root next to `ToastProvider`) replaces every remaining native `confirm()`/`window.confirm()` call (customer archive, task delete, quote-section delete) with a consistent styled, Escape/backdrop-dismissible dialog. |
| M6 | No composite index on `(company_id, status)` / `(company_id, lead_source)` | Performance | **[FIXED in 2.9.1]** Added `Index("company_id", "status")` and `Index("company_id", "lead_source")` on `Customer`, and the equivalent pair (`status`, `source_channel`) on `Lead` — matching the exact filter combinations `CustomerRepository.list`/`LeadRepository.list` actually issue. Migration `e042f8386f09`. |
| M7 | Refresh tokens cannot be revoked | Security | **Still deferred.** A real Redis-backed denylist is a genuine feature build (revocation semantics, logout-endpoint changes, refresh-endpoint checks), not a fix to existing behavior — out of scope for a "no business logic changes" polish release. Consistent with every prior session's assessment (see `ROADMAP.md`'s change log). |
| M8 | `GetCustomerProfileUseCase` still computes a `contacts` list nobody renders in the current UI | Tech debt | **Reviewed, intentionally left as-is.** `contacts` is part of the tested, documented `GET /crm/customers/{id}/profile` response contract (`tests/crm/test_customers_api.py` asserts on it directly) — removing it now would be a breaking API change, which conflicts with this release's explicit backward-compatibility constraint. Revisit only alongside a deliberate API version bump. |
| M9 | Email fields are unvalidated free text | Validation | **[FIXED in 2.9.1]** `Customer.email`, `Contact.email`, and `Lead.email` on the *input* schemas (`CustomerCreate`/`CustomerUpdate`/`ContactCreate`/`LeadCreate`) now use Pydantic's `EmailStr` (syntax-only; `check_deliverability` stays off, so no network/DNS calls happen on the request path). Output schemas (`CustomerOut`, `LeadOut`, ...) deliberately keep plain `str` so any already-stored malformed email can still be read back without a serialization error. |

## Low

| # | Issue | Category | Status |
|---|---|---|---|
| L1 | Decorative SVG icons missing `aria-hidden` | Accessibility | **[FIXED]** Resolved by Version 2.8.1's accessibility baseline pass — verified still in place during the 2.9.1 re-audit. |
| L2 | No keyboard focus trap / Escape-to-close on dropdown menus | Accessibility | **[FIXED]** Resolved by Version 2.8.1 (`useCloseOnEscape`/`useOutsideClick`) — verified still in place during the 2.9.1 re-audit. |
| L3 | No skip-to-content link | Accessibility | **[FIXED]** Resolved by Version 2.8.1 (`app/layout.tsx`'s `.skip-link`) — verified still in place during the 2.9.1 re-audit. Its link text is still hardcoded English rather than translated (the root layout is a server component outside the client-side `LocaleProvider` tree); left as-is, consistent with the small set of already-documented English-fallback strings noted in `CLAUDE.md`. |
| L4 | Inconsistent page-header subtitles | UI consistency | **[FIXED in 2.9.1]** `CardHeader` gained an optional `subtitle` prop; Customer New and Customer Profile now show one, matching the Dashboard/Customers/Leads pattern. |
| L5 | Filter UI pattern differs between list pages | UI consistency | **Stale finding, no longer applicable.** Re-checked during the 2.9.1 pass: Leads' channel filter and Customers' status filter are both label+`<select>` dropdowns today (the pill/chip pattern this finding described no longer exists, superseded at some point during the 2.8.1 design-system pass). |
| L6 | `core/db/session.py`'s `db_session()` context manager is unused | Tech debt | **[FIXED in 2.9.1]** Removed — confirmed zero call sites anywhere in the codebase before deleting. |
| L7 | Breadcrumb + "Back to list" button both present on Customer Profile | UX redundancy | **[FIXED in 2.9.1]** Removed the redundant "Back to list" button; the breadcrumb already covers that navigation. |

---

## Verification

- Backend: `pytest` — **116/116 passing** (91 pre-existing + 25 new), including dedicated tests for every Critical/High fix:
  - path-traversal filename/module sanitization and a real upload that proves nothing is written outside the storage directory (C1)
  - the app refusing to boot outside development with the default JWT secret, and booting fine with a real one or in development (C2)
  - the login rate limiter blocking past its threshold while tracking IPs independently, end-to-end through `/api/v1/auth/login` (H1)
  - oversized uploads rejected with `VALIDATION_ERROR`, undersized ones accepted (H2)
  - upload blocked for `viewer` role, allowed for `rep`+ (H3)
  - `next_cursor` null when a page is complete, set and traversable to a real second page when not, malformed cursors failing open to page one — for both Customers and Leads (H4)
  - `assigned_manager_id` rejected when it doesn't resolve to a member of the active company, including a cross-tenant UUID, on both create and update (H5)
- Frontend: `tsc --noEmit` and `next build` clean (all 8 routes).
- No new features, routes, or modules were introduced — every change in this pass is a fix to existing, already-shipped behavior.

### 2026-07-07 re-audit (Version 2.9.1 "Enterprise Polish")

Every Medium/Low item above was re-checked against the current codebase (10 modules, 8 versions later) rather than assumed still valid from the original 2026-06-30 pass. Result: M1, M4, M5, M6, M9, L4, L6, L7 were genuinely still outstanding and fixed directly; M3, L1, L2, L3 had already been resolved by Version 2.8.1 and were verified rather than re-fixed; L5 was a stale finding no longer reflecting the current UI; M2 and M7 remain consciously deferred (both are scoped feature/schema decisions, not fixes, and out of bounds for a "no business logic changes" release); M8 was reviewed and left alone specifically because removing it now would break a tested API contract. Full backend suite passing (492/492, including 3 new tests for the M1 allowlist and 1 for M9's email validation), frontend `tsc --noEmit` and `next build` both clean.
