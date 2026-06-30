"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCloseOnEscape, useOutsideClick } from "@/lib/use-outside-click";

/** Available from every authenticated screen (not just the Dashboard or
 * list pages) so a manager mid-way through a customer profile can start a
 * new record without first navigating back to a list page. */
export function QuickCreateMenu() {
  const t = useTranslations("quickCreate");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useOutsideClick(containerRef, () => setOpen(false));
  useCloseOnEscape(open, () => setOpen(false));

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t("title")}
        className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-white hover:bg-primary-hover"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
          <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-10 mt-1 w-48 rounded-md border border-border bg-surface py-1 shadow-lg">
          <p className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-text-secondary">{t("title")}</p>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push("/crm/customers/new");
            }}
            className="flex w-full items-center px-3 py-2 text-left text-sm text-text-primary hover:bg-bg"
          >
            {t("newCustomer")}
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push("/crm/leads");
            }}
            className="flex w-full items-center px-3 py-2 text-left text-sm text-text-primary hover:bg-bg"
          >
            {t("newLead")}
          </button>
        </div>
      )}
    </div>
  );
}
