# G-STONE ERP Frontend — CRM Module Screens (Phase 2)

Next.js 15 + TypeScript. Implements the CRM screens against the backend's `/api/v1/crm/*` and `/api/v1/auth/*` APIs:

- `/login` — email/password login + company switcher
- `/crm/customers` — customer list (active/archived toggle)
- `/crm/customers/new` — create customer (+ optional primary contact)
- `/crm/customers/[id]` — full customer profile: contact info, company, assigned manager, lead source, advertising campaign, projects/quotes/orders/payments (empty until those modules are installed), notes, attachments, activity timeline
- `/crm/leads` — lead capture form (Instagram/Facebook/Messenger/WhatsApp/Manual), channel filter, convert-to-customer action

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
