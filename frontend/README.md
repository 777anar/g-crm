# G-ERP Frontend — CRM Module Screens (Phase 2)

Next.js 15 + TypeScript. Implements the CRM screens against the backend's `/api/v1/crm/*` and `/api/v1/auth/*` APIs:

- `/login` — email/password login + company switcher
- `/crm/customers` — customer list (active/archived toggle)
- `/crm/customers/new` — create customer (+ optional primary contact)
- `/crm/customers/[id]` — full customer profile: contact info, company, assigned manager, lead source, advertising campaign, projects/quotes/orders/payments (empty until those modules are installed), notes, attachments, activity timeline
- `/crm/leads` — lead capture form (Instagram/Facebook/Messenger/WhatsApp/Manual), channel filter, convert-to-customer action

## Setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

Requires the backend running at `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`).

## Status

> **Not yet runtime-verified.** This code was written without a Node.js environment available in the authoring sandbox (no `node`/`npm` present), so `npm install`, `next build`, and a live browser check have not been run. Code follows Next.js 15 App Router and TypeScript conventions throughout and is believed correct, but please run `npm install && npm run build` and click through the screens before treating this as production-verified.

## Design system

Colors, typography, and component rules come directly from [`UI_UX_GUIDELINES.md`](../UI_UX_GUIDELINES.md) — see `tailwind.config.ts` and `app/globals.css` for the token values, and `components/ui/` for the shared primitives (Button, Badge, Card, Field, EmptyState).
