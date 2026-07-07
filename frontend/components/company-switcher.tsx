"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { me, selectCompany } from "@/lib/api/auth";
import { listMyCompanies } from "@/lib/api/companies";
import { setAccessToken } from "@/lib/session";
import type { Company } from "@/lib/types";
import { DropdownItem, DropdownPanel, useDropdown } from "@/components/ui/dropdown";

export function CompanySwitcher() {
  const t = useTranslations("company");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [switching, setSwitching] = useState(false);
  const { open, containerRef, toggle, close } = useDropdown();

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

  async function handleSelect(companyId: string) {
    if (companyId === activeCompanyId) {
      close();
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
      close();
    }
  }

  const activeCompany = companies.find((c) => c.id === activeCompanyId);

  if (!activeCompany) return null;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={toggle}
        disabled={switching}
        className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-text-primary hover:bg-bg disabled:opacity-50"
      >
        <span>{activeCompany.name}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-text-secondary" aria-hidden>
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <DropdownPanel label={t("switchCompany")}>
          {companies.map((company) => (
            <DropdownItem key={company.id} active={company.id === activeCompanyId} onClick={() => handleSelect(company.id)}>
              {company.name}
            </DropdownItem>
          ))}
        </DropdownPanel>
      )}
    </div>
  );
}
