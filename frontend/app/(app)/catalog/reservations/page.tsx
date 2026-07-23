"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { listReservations, releaseSlabReservation } from "@/lib/api/catalog";
import type { ReservationStatus, SlabReservation } from "@/lib/types";
import { RESERVATION_STATUSES } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { usePermission } from "@/lib/permissions";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { useToast } from "@/components/ui/toast";
import { formatDateTime } from "@/lib/format";

const STATUS_TONE: Record<ReservationStatus, "success" | "neutral" | "warning"> = {
  active: "success",
  released: "neutral",
  consumed: "neutral",
};

export default function ReservationsPage() {
  const t = useTranslations("catalog");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");
  const canWrite = usePermission("catalog:slabs:write");
  const toast = useToast();

  const [reservations, setReservations] = useState<SlabReservation[] | null>(null);
  const [statusFilter, setStatusFilter] = useState<ReservationStatus | "">("active");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [releasingId, setReleasingId] = useState<string | null>(null);

  const reload = useCallback(
    async (options: { append?: boolean; cursor?: string } = {}) => {
      try {
        const res = await listReservations({ status: statusFilter || undefined, cursor: options.cursor });
        setReservations((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
        setNextCursor(res.next_cursor);
      } catch (err) {
        setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
      }
    },
    [statusFilter, t]
  );

  useEffect(() => {
    setReservations(null);
    reload();
  }, [reload]);

  async function handleRelease(id: string) {
    setReleasingId(id);
    try {
      await releaseSlabReservation(id);
      toast.success(t("reservationReleased"));
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setReleasingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("slabs"), href: "/catalog/slabs" }, { label: t("reservationsTitle") }]} />

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("reservationsTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("reservationsSubtitle")}</p>
      </div>

      <div className="flex items-center gap-2">
        <label htmlFor="reservation-status-filter" className="text-sm text-text-secondary">
          {tCommon("filters")}
        </label>
        <select
          id="reservation-status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ReservationStatus | "")}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        >
          <option value="">{tCommon("allStatuses")}</option>
          {RESERVATION_STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(`reservationStatus_${s}` as Parameters<typeof t>[0])}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {reservations === null && !error && <TableSkeleton rows={6} columns={6} />}

      {reservations && reservations.length === 0 && (
        <EmptyState title={t("noReservationsYet")} description={t("noReservationsDesc")} />
      )}

      {reservations && reservations.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("colOrderId")}</th>
                  <th className="px-4 py-2 font-medium">{t("colOrderItemId")}</th>
                  <th className="px-4 py-2 font-medium">{t("colSlabId")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-4 py-2 font-medium">{t("colReservedAt")}</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {reservations.map((r) => (
                  <tr key={r.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-mono text-xs text-text-secondary">{r.order_id}</td>
                    <td className="px-4 py-2 font-mono text-xs text-text-secondary">{r.order_item_id}</td>
                    <td className="px-4 py-2 font-mono text-xs text-text-secondary">{r.slab_id}</td>
                    <td className="px-4 py-2">
                      <Badge tone={STATUS_TONE[r.status]}>
                        {t(`reservationStatus_${r.status}` as Parameters<typeof t>[0])}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-text-secondary">
                      {r.reserved_at ? formatDateTime(r.reserved_at) : tCommon("dash")}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {canWrite && r.status === "active" && (
                        <Button
                          variant="secondary"
                          loading={releasingId === r.id}
                          onClick={() => handleRelease(r.id)}
                        >
                          {t("release")}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={() => reload({ append: true, cursor: nextCursor })}>
                {tCommon("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
