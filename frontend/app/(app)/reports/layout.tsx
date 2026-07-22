"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

const TABS = [
  { labelKey: "tabExecutive", href: "/reports" },
  { labelKey: "tabSales", href: "/reports/sales" },
  { labelKey: "tabInventory", href: "/reports/inventory" },
  { labelKey: "tabProduction", href: "/reports/production" },
  { labelKey: "tabProductionPlanning", href: "/reports/production-planning" },
  { labelKey: "tabInstallation", href: "/reports/installation" },
  { labelKey: "tabFinance", href: "/reports/finance" },
] as const;

export default function ReportsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const t = useTranslations("reports");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      <div className="flex gap-1 border-b border-border">
        {TABS.map((tab) => {
          // Exact-or-subpath match with a trailing-slash boundary -- "/reports/production"
          // must not read as active while viewing "/reports/production-planning" just
          // because one href is a string-prefix of the other.
          const active =
            tab.href === "/reports"
              ? pathname === "/reports"
              : pathname === tab.href || pathname?.startsWith(`${tab.href}/`);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`border-b-2 px-3 py-2 text-sm font-medium ${
                active
                  ? "border-primary text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              {t(tab.labelKey)}
            </Link>
          );
        })}
      </div>

      {children}
    </div>
  );
}
