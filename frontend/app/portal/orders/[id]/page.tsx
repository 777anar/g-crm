"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { getPortalOrder } from "@/lib/api/portal";
import type { PortalOrder } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, CardHeader } from "@/components/ui/card";
import { OrderStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";

export default function PortalOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("portal");
  const [order, setOrder] = useState<PortalOrder | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortalOrder(id)
      .then(setOrder)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !order) return <TableSkeleton rows={5} columns={3} />;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: t("nav.orders"), href: "/portal/orders" }, { label: order.order_number }]} />

      <div className="flex items-center gap-3">
        <h1 className="font-mono text-xl font-semibold text-text-primary">{order.order_number}</h1>
        <OrderStatusBadge status={order.status} />
      </div>

      <Card>
        <CardHeader title={t("orderDetails")} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs text-text-secondary">{t("subtotal")}</p>
            <p className="text-sm text-text-primary">
              {order.currency} {parseFloat(order.subtotal_gross).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("discount")}</p>
            <p className="text-sm text-text-primary">
              {order.currency} {parseFloat(order.discount_amount).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("vat")}</p>
            <p className="text-sm text-text-primary">
              {order.currency} {parseFloat(order.vat_amount).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("total")}</p>
            <p className="text-base font-semibold text-text-primary">
              {order.currency} {parseFloat(order.total_final).toFixed(2)}
            </p>
          </div>
          {order.delivery_address && (
            <div className="sm:col-span-2">
              <p className="text-xs text-text-secondary">{t("deliveryAddress")}</p>
              <p className="text-sm text-text-primary">{order.delivery_address}</p>
            </div>
          )}
          {order.scheduled_production_date && (
            <div>
              <p className="text-xs text-text-secondary">{t("scheduledProduction")}</p>
              <p className="text-sm text-text-primary">{formatDate(order.scheduled_production_date)}</p>
            </div>
          )}
          {order.scheduled_installation_date && (
            <div>
              <p className="text-xs text-text-secondary">{t("scheduledInstallation")}</p>
              <p className="text-sm text-text-primary">{formatDate(order.scheduled_installation_date)}</p>
            </div>
          )}
        </div>
      </Card>

      <p className="text-xs text-text-secondary">
        {t("created")}: {formatDate(order.created_at)}
      </p>
    </div>
  );
}
