# G-STONE ERP Frontend — CRM + Stone Catalog Screens

Next.js 15 + TypeScript. Implements the CRM screens against the backend's `/api/v1/crm/*` and `/api/v1/auth/*` APIs:

- `/login` — email/password login + company switcher
- `/crm/customers` — customer list (active/archived toggle)
- `/crm/customers/new` — create customer (+ optional primary contact)
- `/crm/customers/[id]` — full customer profile: contact info, company, assigned manager, lead source, advertising campaign, projects/quotes/orders/payments (empty until those modules are installed), notes, attachments, activity timeline
- `/crm/leads` — lead capture form (Instagram/Facebook/Messenger/WhatsApp/Manual), channel filter, convert-to-customer action

And the Stone Catalog screens (Version 2.0) against `/api/v1/catalog/*`:

- `/catalog/brands` — brand list + create
- `/catalog/materials` — material list with brand/collection/status filters, search, sort, cursor-paginated "load more"
- `/catalog/materials/new` — create material (brand → collection cascading select, full spec fields)
- `/catalog/materials/[id]` — material detail: specifications, image upload (gallery/thumbnail/bookmatch), document upload (technical PDF/installation guide/cleaning guide), pricing across every price list, and slabs for this material
- `/catalog/slabs` — slab list with material/warehouse/status filters, search, sort, inline status-change select, create form (computes area client-side on submit via the backend)
- `/catalog/warehouses` — warehouse list + create
- `/catalog/price-lists` — price list list + create
- `/catalog/price-lists/[id]` — manage a price list's per-material cost/sale price entries (upsert)

## Setup

Requires Node.js 20+. If you don't have it (no Homebrew on this Mac), download a prebuilt tarball instead of installing system-wide:

```bash
curl -sL -o /tmp/node.tar.gz "https://nodejs.org/dist/v20.17.0/node-v20.17.0-darwin-x64.tar.gz"
mkdir -p ~/.local && tar -xzf /tmp/node.tar.gz -C ~/.local && mv ~/.local/node-v20.17.0-darwin-x64 ~/.local/node
echo 'export PATH="$HOME/.local/node/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

Then:

```bash
npm install
cp .env.example .env.local
npm run dev
```

Requires the backend running at `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`).

## Status

**Runtime-verified** (2026-06-30): `npm install`, `tsc --noEmit`, and `next build` all succeed with zero errors; all 7 routes compile and respond 200 in both `next build` and `next dev`. No browser extension was available in the verification environment, so visual/click-through QA was not performed — only build success, type-check success, and server-rendered HTML content were confirmed. Recommend a manual click-through before considering this fully production-verified.

## Design system

Colors, typography, and component rules come directly from [`UI_UX_GUIDELINES.md`](../UI_UX_GUIDELINES.md) — see `tailwind.config.ts` and `app/globals.css` for the token values, and `components/ui/` for the shared primitives (Button, Badge, Card, Field, EmptyState).

## Internationalization (i18n)

Built with [next-intl](https://next-intl.dev/). Three languages, no hardcoded UI strings:

- **Default**: Azerbaijani (`az`)
- **Second**: Russian (`ru`)
- **Fallback**: English (`en`) — any key missing from `az`/`ru` automatically falls back to the English value (see `lib/i18n/config.ts`'s `deepMerge`).

Translation files: [`locales/az.json`](locales/az.json), [`locales/ru.json`](locales/ru.json), [`locales/en.json`](locales/en.json).

**Architecture note**: this app does not use next-intl's URL-based routing (no `/az/...`, `/ru/...` path segments) — existing routes (`/login`, `/dashboard`, `/crm/customers`, ...) are unchanged. Instead, `lib/i18n/locale-context.tsx` provides a client-side `LocaleProvider` (wrapping `NextIntlClientProvider`) that holds the active locale in React state and renders the corresponding merged message set. This was a deliberate choice to localize the UI without restructuring the route tree.

**Persistence**: the selected language is saved to `localStorage` (`g_erp_locale`) and restored on next visit — "remembered per user" in the practical sense that each user has their own browser profile. There is no per-user locale field in the backend; if multi-device sync of the language preference is needed later, that would mean adding a `locale` column to `users` and a `PATCH /api/v1/auth/me` endpoint — out of scope for this pass.

**Switching language**: the globe/flag dropdown in the top header (`components/language-switcher.tsx`), available on every authenticated page and on `/login`.

**Known limitation**: a handful of strings are generated server-side and stored as data (e.g. the system activity-timeline entry "Customer 'X' created."). These come from the backend's audit/activity records, not frontend components, so they are not covered by this frontend-only i18n pass and currently always render in English.
