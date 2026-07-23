"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { hasPortalSession, clearPortalSession } from "@/lib/portal-session";
import { portalLogout } from "@/lib/api/portal";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";

const NAV_ITEMS = [
  { key: "dashboard", href: "/portal/dashboard" },
  { key: "orders", href: "/portal/orders" },
  { key: "quotes", href: "/portal/quotes" },
  { key: "invoices", href: "/portal/invoices" },
  { key: "installation", href: "/portal/installation" },
  { key: "documents", href: "/portal/documents" },
] as const;

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("portal");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (pathname === "/portal/login") {
      setReady(true);
      return;
    }
    if (!hasPortalSession()) {
      router.replace("/portal/login");
      return;
    }
    setReady(true);
  }, [router, pathname]);

  async function handleLogout() {
    await portalLogout().catch(() => {});
    clearPortalSession();
    router.push("/portal/login");
  }

  if (!ready) return null;
  if (pathname === "/portal/login") return <>{children}</>;

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
              GS
            </div>
            <span className="text-sm font-semibold text-text-primary">{t("brandTitle")}</span>
          </div>
          <nav className="flex flex-wrap items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const active = pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                    active ? "bg-primary/10 text-primary" : "text-text-secondary hover:bg-bg hover:text-text-primary"
                  }`}
                >
                  {t(`nav.${item.key}`)}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
            <button
              onClick={handleLogout}
              className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-bg hover:text-text-primary"
            >
              {t("logout")}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  );
}
