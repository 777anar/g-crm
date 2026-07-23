"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  BarChart3,
  CircleDollarSign,
  LayoutDashboard,
  Menu,
  Package,
  Settings as SettingsIcon,
  TrendingUp,
  X,
  type LucideIcon,
} from "lucide-react";
import { clearSession } from "@/lib/session";
import { logout as logoutRequest } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { CompanySwitcher } from "@/components/company-switcher";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { QuickCreateMenu } from "@/components/quick-create-menu";
import { useCloseOnEscape, useFocusTrap } from "@/lib/use-outside-click";

// G-STONE ERP Executive, Milestone 2: the app is repositioned from "a CRM"
// to an executive ERP, so the primary sidebar collapses further -- from the
// 9 module-level sections Sprint 2 established down to the 5 modules the
// owner actually needs to read the business (plus Settings as baseline
// chrome, not a business module). Customers/Leads/Tasks/Projects/Orders
// merge into one "Sales" pipeline (cross-linked via `SalesSectionTabs`);
// Catalog keeps its own URL/data model but is relabeled "Inventory" in the
// nav, matching ROADMAP.md's own framing of Catalog as the inventory
// system; Production/Installation/Messages move to secondary-only, same as
// every other page that "moved out of primary nav but still exists" --
// nothing was deleted, only regrouped, exactly as Sprint 2's own comment
// (preserved below in spirit) established for the prior regrouping.
const NAV_ITEMS = [
  { labelKey: "dashboard", href: "/dashboard" },
  { labelKey: "sales", href: "/crm/customers" },
  { labelKey: "inventory", href: "/catalog/materials" },
  { labelKey: "finance", href: "/finance/invoices" },
  { labelKey: "reports", href: "/reports" },
  { labelKey: "settings", href: "/settings" },
] as const;

// Routes that live outside the primary sidebar but still need the browser
// tab title / active-section logic in the effect below -- kept as a separate
// list so NAV_ITEMS above stays exactly the visible primary sections.
const SECONDARY_ROUTES = [
  { labelKey: "leads", href: "/crm/leads" },
  { labelKey: "tasks", href: "/crm/tasks" },
  { labelKey: "projects", href: "/sales/projects" },
  { labelKey: "orders", href: "/orders" },
  { labelKey: "brands", href: "/catalog/brands" },
  { labelKey: "slabs", href: "/catalog/slabs" },
  { labelKey: "warehouses", href: "/catalog/warehouses" },
  { labelKey: "priceLists", href: "/catalog/price-lists" },
  { labelKey: "expenses", href: "/finance/expenses" },
  { labelKey: "production", href: "/production" },
  { labelKey: "installation", href: "/installation" },
  { labelKey: "inbox", href: "/communication/inbox" },
  { labelKey: "channels", href: "/communication/channels" },
  { labelKey: "integrations", href: "/communication/integrations" },
  { labelKey: "messageTemplates", href: "/communication/templates" },
  { labelKey: "aiAssistant", href: "/ai/dashboard" },
  { labelKey: "suppliers", href: "/purchasing/suppliers" },
  { labelKey: "purchaseOrders", href: "/purchasing/orders" },
  { labelKey: "campaigns", href: "/marketing/campaigns" },
  { labelKey: "cutOptimization", href: "/cut-optimization" },
  { labelKey: "offcutLibrary", href: "/catalog/offcuts" },
] as const;

// One Lucide icon per primary section -- replaces the hand-drawn inline SVG
// path set this map used to hold (UI_UX_GUIDELINES.md section 2 always
// called for "a single consistent icon library (e.g., Lucide)"; the inline
// paths were an explicit, deliberate deferral of that decision, not an
// oversight). Every consumer (the full labeled sidebar and the tablet
// icon-only rail below) renders the same icon per section from this one map.
const NAV_ICONS: Record<(typeof NAV_ITEMS)[number]["labelKey"], LucideIcon> = {
  dashboard: LayoutDashboard,
  sales: TrendingUp,
  inventory: Package,
  finance: CircleDollarSign,
  reports: BarChart3,
  settings: SettingsIcon,
};

function NavLinks({ pathname, onNavigate }: { pathname: string | null; onNavigate?: () => void }) {
  const tNav = useTranslations("nav");
  return (
    <ul className="flex flex-col gap-0.5">
      {NAV_ITEMS.map((item) => {
        const active = pathname?.startsWith(item.href);
        const Icon = NAV_ICONS[item.labelKey];
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-md border-l-2 px-2.5 py-2 text-sm font-medium transition-colors ${
                active
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-transparent text-text-secondary hover:bg-bg hover:text-text-primary"
              }`}
            >
              <Icon size={18} strokeWidth={1.4} aria-hidden className="shrink-0" />
              <span className="truncate">{tNav(item.labelKey)}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

// Icon-only collapsed sidebar for the tablet breakpoint (md to <lg, i.e.
// 768-1023px), per UI_UX_GUIDELINES.md section 7's tablet spec -- previously
// tablet widths fell all the way back to the phone-width slide-over drawer,
// which this replaces with a persistent, always-visible rail (no open/close
// state, unlike the drawer) so a tablet user doesn't have to open a menu to
// navigate at all. Each entry's label is still available via `title` (native
// tooltip) and `aria-label`, since there's no visible text at this width.
function NavIconRail({ pathname }: { pathname: string | null }) {
  const tNav = useTranslations("nav");
  return (
    <ul className="flex flex-col items-center gap-1">
      {NAV_ITEMS.map((item) => {
        const active = pathname?.startsWith(item.href);
        const Icon = NAV_ICONS[item.labelKey];
        const label = tNav(item.labelKey);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              aria-current={active ? "page" : undefined}
              aria-label={label}
              title={label}
              className={`flex h-10 w-10 items-center justify-center rounded-md border-l-2 transition-colors ${
                active
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-transparent text-text-secondary hover:bg-bg hover:text-text-primary"
              }`}
            >
              <Icon size={20} strokeWidth={1.4} aria-hidden />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const mobileNavRef = useRef<HTMLElement>(null);
  useCloseOnEscape(mobileNavOpen, () => setMobileNavOpen(false));
  useFocusTrap(mobileNavRef, mobileNavOpen);

  function handleLogout() {
    // Best-effort: revoke server-side (the refresh token rides along as an
    // httpOnly cookie -- see lib/api/auth.ts) even though the client already
    // discards its own session state and redirects regardless of the outcome.
    logoutRequest().catch(() => {});
    clearSession();
    router.push("/login");
  }

  // Every route lives under this one client-side layout with no per-page
  // <title>/generateMetadata, so the browser tab is kept in sync here --
  // matched against the longest NAV_ITEMS href prefix, since detail routes
  // (e.g. /crm/customers/[id]) should show their parent section's title.
  useEffect(() => {
    if (!pathname) return;
    const match = [...NAV_ITEMS, ...SECONDARY_ROUTES]
      .sort((a, b) => b.href.length - a.href.length)
      .find((item) => pathname.startsWith(item.href));
    document.title = match ? `${tNav(match.labelKey)} · ${tCommon("appName")}` : tCommon("appName");
  }, [pathname, tNav, tCommon]);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="print-hidden flex h-14 items-center justify-between border-b border-border bg-surface px-3 sm:px-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMobileNavOpen(true)}
            aria-label={tCommon("openNavigation")}
            className="flex h-8 w-8 items-center justify-center rounded-md text-text-secondary hover:bg-bg hover:text-text-primary md:hidden"
          >
            <Menu size={18} strokeWidth={1.5} aria-hidden />
          </button>
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
            GS
          </div>
          <span className="hidden font-semibold text-text-primary sm:inline">{tCommon("appName")}</span>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <QuickCreateMenu />
          <CompanySwitcher />
          <LanguageSwitcher />
          <ThemeToggle />
          <Button variant="secondary" onClick={handleLogout}>
            {tCommon("signOut")}
          </Button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav
          aria-label={tCommon("mainNavigation")}
          className="hidden w-56 shrink-0 overflow-y-auto border-r border-border bg-surface p-3 lg:block"
        >
          <NavLinks pathname={pathname} />
        </nav>

        <nav
          aria-label={tCommon("mainNavigation")}
          className="hidden shrink-0 overflow-y-auto border-r border-border bg-surface p-2 md:block lg:hidden"
        >
          <NavIconRail pathname={pathname} />
        </nav>

        {mobileNavOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div
              className="absolute inset-0 bg-black/40"
              onClick={() => setMobileNavOpen(false)}
              aria-hidden
            />
            <nav
              ref={mobileNavRef}
              aria-label={tCommon("mainNavigation")}
              className="absolute inset-y-0 left-0 w-64 max-w-[80vw] overflow-y-auto border-r border-border bg-surface p-3 shadow-elevated"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="font-semibold text-text-primary">{tCommon("appName")}</span>
                <button
                  type="button"
                  onClick={() => setMobileNavOpen(false)}
                  aria-label={tCommon("closeNavigation")}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-text-secondary hover:bg-bg hover:text-text-primary"
                >
                  <X size={16} strokeWidth={1.5} aria-hidden />
                </button>
              </div>
              <NavLinks pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
            </nav>
          </div>
        )}

        <main id="main-content" className="min-w-0 flex-1 p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
