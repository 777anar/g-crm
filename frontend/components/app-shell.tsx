"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { clearAccessToken } from "@/lib/session";
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

function NavLinks({ pathname, onNavigate }: { pathname: string | null; onNavigate?: () => void }) {
  const tNav = useTranslations("nav");
  return (
    <ul className="flex flex-col gap-1">
      {NAV_ITEMS.map((item) => {
        const active = pathname?.startsWith(item.href);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`block rounded-md px-3 py-2 text-sm font-medium ${
                active ? "bg-primary text-white" : "text-text-primary hover:bg-bg"
              }`}
            >
              {tNav(item.labelKey)}
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
