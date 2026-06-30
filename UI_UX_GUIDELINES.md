# G-ERP — UI/UX Guidelines

_Date: 2026-06-29_
_Status: Phase 1 design document. Derived from the frozen [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) architecture — Next.js 15 + TypeScript frontend, per-module navigation driven by each module's `navigation.py` contribution, multi-company context, future mobile parity._

---

## 1. Design Principles

1. **One system, many companies** — the UI must make the active company (G-STONE GALLERY / KORONA PREMIUM / NEOLITH BAKU) unmistakable at all times, since the same user may switch contexts during a session.
2. **Module-aware, not module-cluttered** — only navigation/UI for a company's `enabled_modules` renders; a company with CRM+Sales only never sees Production/Installation menus.
3. **Operational clarity over decoration** — this is a working tool for sales, warehouse, production, and installation staff, not a marketing site. Density and scanability win over whitespace-heavy minimalism, especially in list/table views.
4. **Consistent regardless of module** — a user moving from CRM to Inventory to Production should not have to relearn interaction patterns; every module's UI follows the same component and layout rules defined here.
5. **Designed for eventual mobile parity** — layouts and components are built mobile-responsive from day one, not retrofitted, anticipating the future native mobile client (frozen architecture §4.7).

## 2. Design System Foundation

- **Component library base**: Tailwind CSS + a headless component primitive layer (e.g., Radix UI / shadcn/ui pattern) — gives full control over visual design while avoiding building low-level interaction primitives (dialogs, dropdowns, comboboxes) from scratch.
- **Design tokens**: colors, spacing, typography, radii, and shadows defined as a token set (Tailwind config + CSS variables) so theming (e.g., per-company subtle branding accents, light/dark mode later) is a token swap, not a component rewrite.
- **Icon set**: a single consistent icon library (e.g., Lucide) used everywhere — no mixing icon sets across modules.

## 3. Color Palette

Base palette is neutral-first (operational tool, not a consumer brand surface), with one primary accent and standard semantic colors. Company branding (logo) is shown in the header/company switcher but does **not** retheme the whole application per company — consistency across companies matters more than per-company brand identity for an internal ops tool.

| Token | Hex (reference) | Usage |
|---|---|---|
| `--color-bg` | `#F8F9FB` | App background |
| `--color-surface` | `#FFFFFF` | Cards, panels, tables |
| `--color-border` | `#E2E5EA` | Dividers, table borders, input borders |
| `--color-text-primary` | `#16181D` | Primary text |
| `--color-text-secondary` | `#5B6270` | Secondary/meta text |
| `--color-primary` | `#1F4FD8` | Primary actions, links, active nav |
| `--color-primary-hover` | `#173EAD` | Primary hover state |
| `--color-success` | `#1A8754` | Won deals, completed jobs, positive states |
| `--color-warning` | `#B8860B` | Pending/at-risk states (overdue task, low stock) |
| `--color-danger` | `#C0392B` | Lost deals, errors, destructive actions |
| `--color-info` | `#0E7C9D` | Informational badges, in-progress states |

Semantic colors are reused identically across modules: e.g., `--color-warning` always means "needs attention" whether it's an overdue CRM task, a low-stock Inventory alert, or a delayed Installation job — so users build one mental model that transfers across the whole platform.

Dark mode is not required for Phase 1 but token-based theming means it is a later, low-cost addition (swap CSS variable values, no component rewrites).

## 4. Typography

- **Font**: a single system-friendly sans-serif (e.g., Inter) for both UI and data-dense tables — optimized for legibility at small sizes, since tables (inventory lists, deal lists, order lines) are a dominant UI pattern here.
- **Scale**:

| Token | Size / Line-height | Usage |
|---|---|---|
| `text-xs` | 12px / 16px | Table meta, timestamps, badges |
| `text-sm` | 14px / 20px | Default body text, table cell content, form labels |
| `text-base` | 16px / 24px | Primary content, form inputs |
| `text-lg` | 18px / 28px | Card titles, section headers |
| `text-xl` | 22px / 30px | Page titles |
| `text-2xl` | 28px / 36px | Dashboard headline metrics |

- **Weight usage**: regular (400) for body, medium (500) for emphasis/labels, semibold (600) reserved for page titles and key metrics — bold is used sparingly so it retains visual weight where it appears.
- **Numeric data** (money, quantities, IDs): tabular-nums font feature enabled so columns of numbers align — important across Sales totals, Inventory quantities, Finance amounts.

## 5. Component Rules

### 5.1 General
- Every interactive component (button, input, select, dialog) has defined **default, hover, focus, active, disabled** states using the token palette — no ad hoc one-off styling per module.
- Focus states must be visible (accessibility) — never `outline: none` without a replacement focus ring.
- Loading states use skeleton placeholders for content areas (tables, cards), not blocking full-page spinners, except for full-page initial load/auth checks.

### 5.2 Buttons
- **Primary**: filled, `--color-primary` — one primary action per view/section maximum (e.g., "Create Deal," "Approve Order").
- **Secondary**: outlined/neutral — supporting actions (Cancel, Export).
- **Destructive**: `--color-danger` outline, filled only on final confirmation step — destructive actions (delete contact, cancel order) always require a confirmation dialog stating the consequence in plain language, not just "Are you sure?".
- **Icon-only buttons** always carry an accessible label (`aria-label`) and a tooltip on hover.

### 5.3 Forms
- Labels always visible above the field (no placeholder-as-label pattern) — placeholders are reserved for format hints (e.g., "+994 XX XXX XX XX").
- Validation errors appear inline beneath the field, in `--color-danger`, matching the API's `VALIDATION_ERROR` field-level `details` array (§6 of API_SPECIFICATION.md) one-to-one — every backend validation error must be mappable to a specific field in the form.
- Money fields always show currency alongside the amount (matching the API's `{amount, currency}` shape) — never a bare number with currency implied.
- Multi-step flows (e.g., Lead → Convert to Deal, Quote → Order) use a clear step indicator, not a single overloaded form.

### 5.4 Tables / List Views
The dominant UI pattern across nearly every module (contacts, deals, stock items, work orders, invoices). Rules:
- Sticky header row.
- Column sort indicators match the API's `?sort=field` / `?sort=-field` convention.
- Row-level status is always shown via a **badge** using the semantic color tokens (§3), never color-only without text (accessibility — color is reinforcement, not the sole signal).
- Pagination uses "Load more" / cursor-based infinite scroll on mobile-width viewports, and a cursor-driven "Next/Previous" control on desktop — both backed by the same cursor pagination API (§4 of API_SPECIFICATION.md), never offset-based UI assumptions.
- Bulk actions (multi-select rows) supported wherever the underlying API supports batch operations; introduced module-by-module as needed, not assumed everywhere.
- Empty states always explain *why* the list is empty and offer the primary creation action (e.g., "No deals yet — Create your first deal"), never a bare "No data."

### 5.5 Cards / Detail Panels
- Entity detail views (a Contact, a Deal, a Work Order) follow a consistent layout: header (title + status badge + primary actions) → key fields in a left column → activity/timeline/related-records in a right column or below — this layout repeats across modules so users transfer the pattern.
- Cross-module relationships (e.g., a Deal showing its linked Account, a Sales Order showing its linked Quote) are rendered as clickable reference chips, navigating to that record's detail view in the owning module.

### 5.6 Dialogs / Modals
- Used for focused, single-task actions (confirm delete, quick-create a contact from within a deal form) — not for complex multi-section forms, which get a full page instead.
- Always dismissible via Escape key and an explicit close control, never only by clicking outside (prevents accidental data loss on misclick).

### 5.7 Notifications / Toasts
- Transient toasts for action confirmations ("Deal updated") — auto-dismiss, non-blocking.
- Persistent in-app notification center for async/event-driven outcomes (per the frozen EDA architecture) — e.g., "Production finished for Order #1234," "AI document analysis complete" — since these don't originate from the current user's direct action and must not be missed if the user has navigated away.

## 6. Navigation

### 6.1 Structure
- **Top bar**: company switcher (left, always visible — shows active company name/logo), global search, user menu, notification bell (right).
- **Primary sidebar**: module-level navigation, rendered dynamically from each enabled module's `navigation.py` contribution (frozen architecture §4.4) — a company with only CRM+Sales+Finance enabled sees exactly those three top-level sections, nothing else.
- **Secondary navigation**: within a module, a sub-nav for its sections (e.g., CRM → Contacts / Accounts / Leads / Deals / Tasks).
- Breadcrumbs on detail pages (`CRM > Deals > Acme Corp Renovation`) so users always know their location, especially important once navigation spans many modules.

### 6.2 Company Switching
- Switching companies via the top-bar switcher triggers the `/api/v1/auth/select-company` flow (API_SPECIFICATION.md §2.1), reloads the active module set, and returns the user to that module's landing page (not mid-record in a different company's data, to avoid confusion about context).
- The active company name/logo is persistently visible in the top bar at all times — never just on a settings page — since misattributing an action to the wrong company is a real risk in a shared multi-tenant UI.

### 6.3 Cross-Module Navigation
- Deep links between modules (e.g., from a Sales Order to its parent Quote, or — once built — from a Work Order to its Sales Order) are always real navigable links, not just text references, reflecting the event-linked relationships in the data model without implying the modules are tightly coupled in code.

## 7. Responsive Behavior

- **Breakpoints** (Tailwind defaults, used consistently): `sm` 640px, `md` 768px, `lg` 1024px, `xl` 1280px.
- **Desktop (≥1024px)**: full sidebar + secondary nav + multi-column detail layouts. Primary target for most operational use (office/warehouse desktop use).
- **Tablet (768–1023px)**: sidebar collapses to icon-only with flyout labels; detail views drop to single column; tables remain but with reduced default visible columns (column chooser available).
- **Mobile (<768px)**: sidebar becomes a bottom nav or slide-over menu; tables convert to stacked card lists (each row becomes a card showing the most important 3–4 fields, full record on tap); forms are single-column and full-width; primary actions move to a fixed bottom action bar where relevant (e.g., "Approve Order" on a small screen).
- Field staff use cases (warehouse stock checks, installation crews logging photos/status on-site) are explicitly mobile-first interactions even within the Phase 1 web app — anticipating that these specific flows are the first candidates for the future native mobile client, so their responsive web behavior should already feel mobile-native, not be an afterthought.
- Image-heavy flows (installation site photos, future AI image analysis results) use a responsive grid that degrades gracefully from multi-column (desktop) to single-column (mobile), with lazy-loaded thumbnails.

## 8. Accessibility Baseline

- Color contrast meets WCAG AA for all text/background token combinations in §3.
- All interactive elements reachable and operable via keyboard (tab order matches visual order).
- Form errors and status badges never rely on color alone (icon/text reinforcement required, per §5.4/§5.3).
- Semantic HTML landmarks (`nav`, `main`, `header`) used in the Next.js layout structure so screen readers can navigate module sections meaningfully.

## 9. Content & Tone

- UI copy is plain, operational, and unambiguous — action labels are verbs ("Approve Order," not "Submit"), status labels match the backend's exact status enum values rendered in human-readable form (e.g., `pending_approval` → "Pending Approval") so there is never a mismatch between what support/engineering sees in logs and what users see on screen.
- Error messages shown to users are derived from the API's `error.message` (API_SPECIFICATION.md §6) but may be rephrased for clarity at the frontend layer — raw backend error codes are never shown directly to end users, only logged (with `request_id`) for support purposes.
- Locale readiness: all user-facing strings go through a translation layer (i18n keys, not hardcoded strings) from Phase 1, even though only English may ship initially — Azerbaijani/Russian are anticipated per the frozen architecture's localization requirement.
