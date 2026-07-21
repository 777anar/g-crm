"use client";

import { useTranslations } from "next-intl";
import { SectionTabs } from "@/components/ui/section-tabs";

/** Shared cross-navigation for the "Sales" module -- Milestone 2 of the
 * G-STONE ERP Executive redesign merges what used to be two separate
 * primary nav sections (Customers/Leads/Tasks under "CRM", Projects/Orders
 * under a standalone "Projects" item) into one Sales pipeline, so every page
 * in that pipeline cross-links to all five instead of just its old sibling
 * group of two or three. */
export function SalesSectionTabs() {
  const tCrm = useTranslations("crm");
  const tNav = useTranslations("nav");
  return (
    <SectionTabs
      items={[
        { label: tCrm("tabCustomers"), href: "/crm/customers" },
        { label: tCrm("tabLeads"), href: "/crm/leads" },
        { label: tCrm("tabTasks"), href: "/crm/tasks" },
        { label: tNav("projects"), href: "/sales/projects" },
        { label: tNav("orders"), href: "/orders" },
      ]}
    />
  );
}
