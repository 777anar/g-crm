"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { me, selectCompany } from "@/lib/api/auth";
import { listMyCompanies } from "@/lib/api/companies";
import { setAccessToken } from "@/lib/session";
import type { Company } from "@/lib/types";
import { useCloseOnEscape, useOutsideClick } from "@/lib/use-outside-click";

export function CompanySwitcher() {
  const t = useTranslations("company");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([me(), listMyCompanies()])
      .then(([profile, companyList]) => {
        setActiveCompanyId(profile.active_company_id);
        setCompanies(companyList);
      })
      .catch(() => {
        // Header degrades gracefully -- the page-level auth guard in
        // app/(app)/layout.tsx already handles redirecting on auth failure.
      });
  }, []);

  useOutsideClick(containerRef, () => setOpen(false));
  useCloseOnEscape(open, () => setOpen(false));

  async function handleSelect(companyId: string) {
    if (companyId === activeCompanyId) {
      setOpen(false);
      return;
    }
    setSwitching(true);
    try {
      const result = await selectCompany(companyId);
      setAccessToken(result.access_token);
      // Full reload: every screen's data is scoped to the active company, so
      // the simplest correct way to guarantee nothing stale is shown is to
      // re-fetch the app from scratch under the new company context.
      window.location.href = "/dashboard";
    } finally {
      setSwitching(false);
      setOpen(false);
    }
  }

  const activeCompany = companies.find((c) => c.id === activeCompanyId);

  if (!activeCompany) return null;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={switching}
        className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-bg disabled:opacity-50"
      >
        <span>{activeCompany.name}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-text-secondary" aria-hidden>
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 top-full z-10 mt-1 w-56 rounded-md border border-border bg-surface py-1 shadow-lg">
          <p className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-text-secondary">
            {t("switchCompany")}
          </p>
          {companies.map((company) => (
            <button
              key={company.id}
              type="button"
              onClick={() => handleSelect(company.id)}
              className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-bg ${
                company.id === activeCompanyId ? "font-semibold text-primary" : "text-text-primary"
              }`}
            >
              {company.name}
              {company.id === activeCompanyId && <span aria-hidden>✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
