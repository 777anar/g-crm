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

## Medium (documented, not fixed this pass)

| # | Issue | Category | Notes |
|---|---|---|---|
| M1 | No upload content-type/extension allowlist | Security | Uploaded files are never served back as executable content today, which limits real-world impact; still worth an allowlist (e.g. images/PDF/office docs) before this is internet-facing. |
| M2 | `customer.type` (individual/business) is now write-only dead weight | Tech debt | The Phase 3 stone-industry form no longer exposes a Type picker (always sends `"individual"`); the column, schema field, and badge logic still exist but are functionally orphaned. Fixing means either reintroducing a Type picker (a feature) or a migration to drop it (riskier than warranted mid-RC) — deferred. |
| M3 | No toast/confirmation feedback on save actions | UX | Status changes, note saves, and customer creation rely on silent reload or navigation as the only feedback. `UI_UX_GUIDELINES.md` §5.7 calls for transient toasts on action confirmation; never implemented. |
| M4 | `CompanySwitcher` and `LanguageSwitcher` duplicate dropdown markup | Duplicate code | Both independently implement the same open/close panel, chevron icon, and checkmark-row pattern. `useOutsideClick` was already extracted; the rendering itself wasn't. Worth a shared `<Dropdown>` primitive. |
| M5 | Native `confirm()` used for customer archive | UX consistency | Every other destructive-action confirmation in the design system is a styled dialog; archive falls back to the browser's native `confirm()`, which looks and behaves inconsistently across browsers/OSes. |
| M6 | No composite index on `(company_id, status)` / `(company_id, lead_source)` | Performance | Each column is individually indexed; fine at current data volumes, but list-with-filter queries will do a less efficient merge once companies have thousands of customers. |
| M7 | Refresh tokens cannot be revoked | Security | `logout` is a client-side token discard only (already documented at implementation time); a stolen refresh token remains valid until natural expiry (30 days). A denylist (Redis, already in the stack) would close this. |
| M8 | `GetCustomerProfileUseCase` still computes a `contacts` list nobody renders | Tech debt | The Phase 3 customer profile page stopped displaying the separate `Contact` sub-entity in favor of the customer's own phone/email/etc. fields, but the backend still queries and returns `contacts[]` in the profile payload, and the contact-creation code path in `CreateCustomerUseCase` is now unreachable from the current UI. Harmless, but dead weight. |
| M9 | Email fields are unvalidated free text | Validation | `Customer.email`, `Contact.email` etc. accept any string — no `EmailStr` format validation server-side (the frontend `<input type="email">` provides only client-side, bypassable validation). |

## Low (documented, not fixed this pass)

| # | Issue | Category | Notes |
|---|---|---|---|
| L1 | Decorative SVG icons missing `aria-hidden` | Accessibility | Chevron/checkmark icons in dropdowns and badges are exposed to assistive tech with no semantic value. |
| L2 | No keyboard focus trap / Escape-to-close on dropdown menus | Accessibility | Company switcher and language switcher close on outside-click but not on `Escape`, and focus isn't moved into the panel on open. |
| L3 | No skip-to-content link | Accessibility | Keyboard users must tab through the full sidebar nav on every page load to reach main content. |
| L4 | Inconsistent page-header subtitles | UI consistency | Dashboard/Customers/Leads show a descriptive subtitle under the page title; Customer Profile/Customer New do not. |
| L5 | Filter UI pattern differs between list pages | UI consistency | Leads page uses pill/chip filters for channel; Customers page uses a `<select>` dropdown for status. Both are reasonable individually but inconsistent side-by-side. |
| L6 | `core/db/session.py`'s `db_session()` context manager is unused | Tech debt | Dead since the event-bus refactor that moved event persistence onto the caller's own session. Zero call sites remain. |
| L7 | Breadcrumb + "Back to list" button both present on Customer Profile | UX redundancy | Two different controls do the same navigation; minor, not confusing, but redundant. |

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
