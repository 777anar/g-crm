"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";

function SettingsCard({ title, description, href }: { title: string; description: string; href: string }) {
  return (
    <Link href={href}>
      <Card className="h-full transition-colors hover:border-primary">
        <h2 className="text-base font-semibold text-text-primary">{title}</h2>
        <p className="mt-1 text-sm text-text-secondary">{description}</p>
      </Card>
    </Link>
  );
}

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tNav = useTranslations("nav");

  const groups: { heading: string; items: { title: string; description: string; href: string }[] }[] = [
    {
      heading: t("groupMessaging"),
      items: [
        { title: tNav("channels"), description: t("channelsDesc"), href: "/communication/channels" },
        { title: tNav("messageTemplates"), description: t("templatesDesc"), href: "/communication/templates" },
        { title: tNav("integrations"), description: t("integrationsDesc"), href: "/communication/integrations" },
      ],
    },
    {
      heading: t("groupCatalog"),
      items: [
        { title: tNav("warehouses"), description: t("warehousesDesc"), href: "/catalog/warehouses" },
        { title: tNav("slabs"), description: t("slabsDesc"), href: "/catalog/slabs" },
        { title: tNav("priceLists"), description: t("priceListsDesc"), href: "/catalog/price-lists" },
      ],
    },
    {
      heading: t("groupProduction"),
      items: [
        { title: t("productionStages"), description: t("productionStagesDesc"), href: "/production/stages" },
        { title: tNav("cutOptimization"), description: t("cutOptimizationDesc"), href: "/cut-optimization" },
        { title: tNav("offcutLibrary"), description: t("offcutLibraryDesc"), href: "/catalog/offcuts" },
        { title: t("productionPlanning"), description: t("productionPlanningDesc"), href: "/reports/production-planning" },
      ],
    },
    {
      heading: t("groupPurchasing"),
      items: [
        { title: tNav("suppliers"), description: t("suppliersDesc"), href: "/purchasing/suppliers" },
        { title: tNav("purchaseOrders"), description: t("purchaseOrdersDesc"), href: "/purchasing/orders" },
      ],
    },
    {
      heading: t("groupMarketing"),
      items: [
        { title: tNav("campaigns"), description: t("campaignsDesc"), href: "/marketing/campaigns" },
      ],
    },
    {
      heading: t("groupOffice"),
      items: [
        { title: tNav("orders"), description: t("ordersDesc"), href: "/orders" },
        { title: tNav("invoices"), description: t("invoicesDesc"), href: "/finance/invoices" },
        { title: tNav("expenses"), description: t("expensesDesc"), href: "/finance/expenses" },
        { title: tNav("aiAssistant"), description: t("aiAssistantDesc"), href: "/ai/dashboard" },
      ],
    },
    {
      heading: t("groupSecurity"),
      items: [
        { title: tNav("security"), description: t("securityDesc"), href: "/settings/security" },
        { title: tNav("auditLog"), description: t("auditLogDesc"), href: "/settings/audit-log" },
      ],
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      {groups.map((group) => (
        <div key={group.heading} className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">{group.heading}</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {group.items.map((item) => (
              <SettingsCard key={item.href} title={item.title} description={item.description} href={item.href} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
