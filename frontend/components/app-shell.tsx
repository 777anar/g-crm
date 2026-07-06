"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { clearAccessToken } from "@/lib/session";
import { Button } from "@/components/ui/button";
import { CompanySwitcher } from "@/components/company-switcher";
import { LanguageSwitcher } from "@/components/language-switcher";
import { QuickCreateMenu } from "@/components/quick-create-menu";

// Dashboard is core-platform navigation, always present regardless of which
// modules are installed. The remaining items mirror each enabled module's
// navigation contribution -- per UI_UX_GUIDELINES.md section 6.1. This list
// mirrors each backend/modules/<name>/navigation.py directly. A future phase
// replaces the module portion with a real GET /nav-config call once
// per-company enablement matters.
const NAV_ITEMS = [
  { labelKey: "dashboard", href: "/dashboard" },
  { labelKey: "customers", href: "/crm/customers" },
  { labelKey: "leads", href: "/crm/leads" },
  { labelKey: "catalog", href: "/catalog/materials" },
  { labelKey: "brands", href: "/catalog/brands" },
  { labelKey: "slabs", href: "/catalog/slabs" },
  { labelKey: "warehouses", href: "/catalog/warehouses" },
  { labelKey: "priceLists", href: "/catalog/price-lists" },
  { labelKey: "projects", href: "/sales/projects" },
  { labelKey: "orders", href: "/orders" },
  { labelKey: "production", href: "/production" },
  { labelKey: "installation", href: "/installation" },
  { labelKey: "invoices", href: "/finance/invoices" },
  { labelKey: "expenses", href: "/finance/expenses" },
  { labelKey: "reports", href: "/reports" },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");

  function handleLogout() {
    clearAccessToken();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
            GS
          </div>
          <span className="font-semibold text-text-primary">{tCommon("appName")}</span>
        </div>
        <div className="flex items-center gap-3">
          <QuickCreateMenu />
          <CompanySwitcher />
          <LanguageSwitcher />
          <Button variant="secondary" onClick={handleLogout}>
            {tCommon("signOut")}
          </Button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav className="w-56 shrink-0 border-r border-border bg-surface p-3">
          <ul className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => {
              const active = pathname?.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
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
        </nav>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
