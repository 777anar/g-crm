"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getPortalMe, listPortalInvoices, listPortalOrders } from "@/lib/api/portal";
import type { PortalInvoice, PortalMe, PortalOrder } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";

export default function PortalDashboardPage() {
  const t = useTranslations("portal");
  const tOrderStatus = useTranslations("orders");
  const [me, setMe] = useState<PortalMe | null>(null);
  const [orders, setOrders] = useState<PortalOrder[]>([]);
  const [invoices, setInvoices] = useState<PortalInvoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPortalMe(), listPortalOrders({ limit: 5 }), listPortalInvoices({ limit: 5 })])
      .then(([meRes, ordersRes, invoicesRes]) => {
        setMe(meRes);
        setOrders(ordersRes.items);
        setInvoices(invoicesRes.items);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <TableSkeleton rows={4} columns={3} />;

  const openBalance = invoices.reduce((sum, inv) => sum + parseFloat(inv.balance_due), 0);
  const activeOrders = orders.filter((o) => o.status !== "completed" && o.status !== "cancelled").length;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("welcome", { name: me?.name ?? "" })}</h1>
        <p className="text-sm text-text-secondary">{me?.company_name}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label={t("activeOrders")} value={activeOrders} tone="info" />
        <StatCard label={t("totalOrders")} value={orders.length} />
        <StatCard
          label={t("openBalance")}
          value={openBalance > 0 ? `${invoices[0]?.currency ?? "AZN"} ${openBalance.toFixed(2)}` : "0.00"}
          tone={openBalance > 0 ? "warning" : "success"}
        />
      </div>

      <Card>
        <CardHeader title={t("recentOrders")} />
        {orders.length === 0 && <p className="text-sm text-text-secondary">{t("noOrdersYet")}</p>}
        {orders.length > 0 && (
          <div className="flex flex-col gap-2">
            {orders.map((o) => (
              <div key={o.id} className="flex items-center justify-between border-b border-border pb-2 last:border-0">
                <div>
                  <p className="font-mono text-sm text-text-primary">{o.order_number}</p>
                  <p className="text-xs text-text-secondary">{formatDate(o.created_at)}</p>
                </div>
                <span className="text-sm text-text-secondary">{tOrderStatus(o.status as any)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
