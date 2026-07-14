"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { clearAccessToken, getRefreshToken } from "@/lib/session";
import { logout as logoutRequest } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { CompanySwitcher } from "@/components/company-switcher";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { QuickCreateMenu } from "@/components/quick-create-menu";
import { useCloseOnEscape } from "@/lib/use-outside-click";

// Sprint 2 ("Layihə" as the primary business object): the primary sidebar is
// deliberately reduced to 9 module-level sections per UI_UX_GUIDELINES.md
// section 6.1 ("Primary sidebar: module-level navigation ... Secondary
// navigation: within a module, a sub-nav for its sections"). Every page that
// used to have its own top-level entry still exists and is still linked from
// somewhere (a SectionTabs bar within its module, or the /settings hub for
// back-office pages that are out of the daily office workflow) -- nothing
// was deleted, only regrouped.
const NAV_ITEMS = [
  { labelKey: "dashboard", href: "/dashboard" },
  { labelKey: "customers", href: "/crm/customers" },
  { labelKey: "projects", href: "/sales/projects" },
  { labelKey: "catalog", href: "/catalog/materials" },
  { labelKey: "production", href: "/production" },
  { labelKey: "installation", href: "/installation" },
  { labelKey: "messages", href: "/communication/inbox" },
  { labelKey: "reports", href: "/reports" },
  { labelKey: "settings", href: "/settings" },
] as const;

// Routes that moved out of the primary sidebar but still need the browser
// tab title / active-section logic in the effect below -- kept as a separate
// list so NAV_ITEMS above stays exactly the 9 visible sections.
const SECONDARY_ROUTES = [
  { labelKey: "leads", href: "/crm/leads" },
  { labelKey: "tasks", href: "/crm/tasks" },
  { labelKey: "brands", href: "/catalog/brands" },
  { labelKey: "slabs", href: "/catalog/slabs" },
  { labelKey: "warehouses", href: "/catalog/warehouses" },
  { labelKey: "priceLists", href: "/catalog/price-lists" },
  { labelKey: "orders", href: "/orders" },
  { labelKey: "invoices", href: "/finance/invoices" },
  { labelKey: "expenses", href: "/finance/expenses" },
  { labelKey: "inbox", href: "/communication/inbox" },
  { labelKey: "channels", href: "/communication/channels" },
  { labelKey: "integrations", href: "/communication/integrations" },
  { labelKey: "messageTemplates", href: "/communication/templates" },
  { labelKey: "aiAssistant", href: "/ai/dashboard" },
] as const;

// Minimal inline line-icons matched to each section, drawn in the same style
// as the existing hamburger/close icons above (stroke currentColor, no new
// icon-library dependency -- an icon set was previously deferred as "a real
// design-system decision"; this keeps that decision small and local instead).
const NAV_ICONS: Record<(typeof NAV_ITEMS)[number]["labelKey"], React.ReactNode> = {
  dashboard: (
    <path d="M2.5 2.5h5v5h-5v-5Zm8 0h5v3.5h-5v-3.5Zm0 6.5h5v6.5h-5v-6.5Zm-8 2h5v4.5h-5v-4.5Z" />
  ),
  customers: (
    <path d="M9 9.25A3.125 3.125 0 1 0 9 3a3.125 3.125 0 0 0 0 6.25Zm0 1.75c-3 0-6 1.5-6 4v.5h12v-.5c0-2.5-3-4-6-4Z" />
  ),
  projects: (
    <path d="M2.5 4.5h4l1.25 1.5H15.5v8.5h-13v-10Z" />
  ),
  catalog: (
    <path d="M2.5 4.5 9 2l6.5 2.5L9 7l-6.5-2.5ZM2.5 8.75 9 11.25l6.5-2.5M2.5 13 9 15.5 15.5 13" />
  ),
  production: (
    <path d="M11.5 2.5 15.5 6.5 13 9l-1.5-1.5-4 4 1 1-2 2-3.5-3.5 2-2 1 1 4-4L8.5 5l3-2.5Z" />
  ),
  installation: (
    <path d="M3 15.5 8 9m-2.5-2 3.5 3.5 5-5-3.5-3.5-5 5Zm7 7 3-3-2-2-3 3 2 2Z" />
  ),
  messages: (
    <path d="M2.5 4h13v8h-8l-3 3v-3h-2v-8Z" />
  ),
  reports: (
    <path d="M3 15.5V9m4 6.5V5.5m4 10V8m4 7.5V2.5" />
  ),
  settings: (
    <path d="M9 11.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm6.25-2.5a6.3 6.3 0 0 1-.08 1l1.58 1.24-1.5 2.6-1.87-.63a6.3 6.3 0 0 1-1.7 1l-.28 1.98h-3l-.28-1.98a6.3 6.3 0 0 1-1.7-1l-1.87.63-1.5-2.6L4.83 10.5a6.3 6.3 0 0 1 0-2L3.25 7.26l1.5-2.6 1.87.63a6.3 6.3 0 0 1 1.7-1l.28-1.98h3l.28 1.98a6.3 6.3 0 0 1 1.7 1l1.87-.63 1.5 2.6-1.58 1.24c.05.33.08.66.08 1Z" />
  ),
};

function NavLinks({ pathname, onNavigate }: { pathname: string | null; onNavigate?: () => void }) {
  const tNav = useTranslations("nav");
  return (
    <ul className="flex flex-col gap-0.5">
      {NAV_ITEMS.map((item) => {
        const active = pathname?.startsWith(item.href);
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
              <svg
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
                className="shrink-0"
              >
                {NAV_ICONS[item.labelKey]}
              </svg>
              <span className="truncate">{tNav(item.labelKey)}</span>
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
  useCloseOnEscape(mobileNavOpen, () => setMobileNavOpen(false));

  function handleLogout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      // Best-effort: revoke server-side even though the client already
      // discards its own tokens and redirects regardless of the outcome.
      logoutRequest(refreshToken).catch(() => {});
    }
    clearAccessToken();
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
            className="flex h-8 w-8 items-center justify-center rounded-md text-text-secondary hover:bg-bg hover:text-text-primary lg:hidden"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
              <path d="M2 4.5h14M2 9h14M2 13.5h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
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

        {mobileNavOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div
              className="absolute inset-0 bg-black/40"
              onClick={() => setMobileNavOpen(false)}
              aria-hidden
            />
            <nav
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
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
                    <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
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
