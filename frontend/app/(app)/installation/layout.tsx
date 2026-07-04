"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

const TABS = [
  { labelKey: "tabDashboard", href: "/installation" },
  { labelKey: "tabCalendar", href: "/installation/calendar" },
  { labelKey: "tabKanban", href: "/installation/kanban" },
  { labelKey: "tabCrews", href: "/installation/crews" },
] as const;

export default function InstallationLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const t = useTranslations("installation");

  // Job detail pages (/installation/jobs/[id]) get their own back-link and
  // shouldn't show the section tab bar meant for the four top-level views.
  const isJobDetail = pathname?.startsWith("/installation/jobs/");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      {!isJobDetail && (
        <div className="flex gap-1 border-b border-border">
          {TABS.map((tab) => {
            const active = tab.href === "/installation" ? pathname === "/installation" : pathname?.startsWith(tab.href);
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
      )}

      {children}
    </div>
  );
}
