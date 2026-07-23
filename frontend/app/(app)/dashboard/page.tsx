"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { checkTaskReminders, getCustomer, listLeads, listTaskNotifications, listTasks } from "@/lib/api/crm";
import { me } from "@/lib/api/auth";
import { listOrders } from "@/lib/api/orders";
import { listProductionNotifications, listWorkOrders } from "@/lib/api/production";
import { listInstallationJobs, listNotifications as listInstallationNotifications } from "@/lib/api/installation";
import { getProject, listMeasurementsForCompany } from "@/lib/api/sales";
import { getExecutiveDashboard, getInventoryAnalytics } from "@/lib/api/reports";
import { fetchAllPages } from "@/lib/fetch-all-pages";
import type {
  ExecutiveDashboard,
  InstallationJob,
  InventoryAnalytics,
  InstallationNotification,
  Lead,
  Order,
  ProductionNotification,
  ProjectItemMeasurement,
  Task,
  TaskNotification,
  WorkOrder,
} from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { StatusBarList, TrendChart, TREND_COLORS } from "@/components/ui/charts";
import {
  Badge,
  InstallationJobStatusBadge,
  LeadStatusBadge,
  OrderStatusBadge,
  TaskPriorityBadge,
} from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { formatDate, formatDateTime, formatNumber } from "@/lib/format";
import { useLeadChannelLabel } from "@/lib/i18n/hooks";
import { usePermission } from "@/lib/permissions";

const ORDER_TERMINAL_STATUSES = new Set(["installed", "completed", "cancelled"]);
const ORDER_PRODUCTION_STAGE_STATUSES = new Set(["waiting", "measuring", "approved_for_production", "in_production"]);
const ORDER_INSTALLATION_STAGE_STATUSES = new Set(["ready", "delivered"]);
const WORK_ORDER_TERMINAL_STATUSES = new Set(["completed", "cancelled"]);
const INSTALLATION_JOB_TERMINAL_STATUSES = new Set(["completed", "cancelled"]);

function toDateKey(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function daysBetween(from: Date, to: Date): number {
  return Math.max(1, Math.round((to.getTime() - from.getTime()) / 86_400_000));
}

type TimelineTone = "neutral" | "info" | "warning" | "danger" | "success";

const DOT_TONE_CLASS: Record<TimelineTone, string> = {
  neutral: "bg-text-secondary",
  info: "bg-info",
  warning: "bg-warning",
  danger: "bg-danger",
  success: "bg-success",
};

function TimelineDot({ tone = "neutral" }: { tone?: TimelineTone }) {
  return <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${DOT_TONE_CLASS[tone]}`} />;
}

type NotificationItem = {
  id: string;
  title: string;
  message: string;
  created_at: string;
  href: string;
};

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const tReports = useTranslations("reports");
  const tOrders = useTranslations("orders");
  const channelLabel = useLeadChannelLabel();
  const canWriteCustomers = usePermission("crm:customers:write");
  const canWriteLeads = usePermission("crm:leads:write");

  const [fullName, setFullName] = useState<string | null>(null);
  const [customerNames, setCustomerNames] = useState<Record<string, string>>({});
  const [projectNames, setProjectNames] = useState<Record<string, string>>({});
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [workOrders, setWorkOrders] = useState<WorkOrder[] | null>(null);
  const [installationJobs, setInstallationJobs] = useState<InstallationJob[] | null>(null);
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [measurementsToday, setMeasurementsToday] = useState<ProjectItemMeasurement[] | null>(null);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [taskNotifications, setTaskNotifications] = useState<TaskNotification[] | null>(null);
  const [installationNotifications, setInstallationNotifications] = useState<InstallationNotification[] | null>(null);
  const [productionNotifications, setProductionNotifications] = useState<ProductionNotification[] | null>(null);
  const [executive, setExecutive] = useState<ExecutiveDashboard | null>(null);
  const [inventory, setInventory] = useState<InventoryAnalytics | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const todayKey = toDateKey(new Date());

    // Promise.allSettled (not Promise.all) so one failing call degrades
    // gracefully -- everything that DID load still renders below, instead
    // of a single rejection blanking the whole page (PROJECT_AUDIT.md B2).
    // The order/work-order/installation-job/task lists are followed to
    // their cursor's end via fetchAllPages rather than a single capped
    // page, so the counts derived from them below never silently
    // under-count past an arbitrary page limit (PROJECT_AUDIT.md B3).
    Promise.allSettled([
      me(),
      fetchAllPages<Order>((cursor) => listOrders({ limit: 100, cursor })),
      fetchAllPages<WorkOrder>((cursor) => listWorkOrders({ limit: 100, cursor })),
      fetchAllPages<InstallationJob>((cursor) => listInstallationJobs({ dateFrom: todayKey, limit: 200, cursor })),
      listLeads({ sort: "-created_at", limit: 5 }),
      listMeasurementsForCompany({ dateFrom: todayKey, dateTo: todayKey }),
      fetchAllPages<Task>((cursor) => listTasks({ excludeTerminal: true, sort: "due_date", limit: 100, cursor })),
      getExecutiveDashboard({ period: "30d" }),
      getInventoryAnalytics(),
    ]).then((results) => {
      const [profileR, orderR, workOrderR, installationR, leadR, measurementR, taskR, executiveR, inventoryR] = results;

      setFullName(profileR.status === "fulfilled" ? profileR.value.full_name : null);
      setOrders(orderR.status === "fulfilled" ? orderR.value : []);
      setWorkOrders(workOrderR.status === "fulfilled" ? workOrderR.value : []);
      setInstallationJobs(installationR.status === "fulfilled" ? installationR.value : []);
      setLeads(leadR.status === "fulfilled" ? leadR.value.items : []);
      setMeasurementsToday(measurementR.status === "fulfilled" ? measurementR.value.items : []);
      setTasks(taskR.status === "fulfilled" ? taskR.value : []);
      setExecutive(executiveR.status === "fulfilled" ? executiveR.value : null);
      setInventory(inventoryR.status === "fulfilled" ? inventoryR.value : null);

      // Surfaces that something was incomplete without hiding whatever DID
      // load -- see the render gates below, which only depend on their own
      // piece of state, not on every call having succeeded.
      const firstFailure = results.find((r): r is PromiseRejectedResult => r.status === "rejected");
      setError(
        firstFailure
          ? firstFailure.reason instanceof ApiRequestError
            ? firstFailure.reason.message
            : t("loadFailed")
          : null
      );
      setLoaded(true);

      // Surfaces newly-due reminders/overdue tasks the moment the
      // Dashboard loads -- see checkTaskReminders' doc comment for why
      // this is a pull rather than a scheduled push. Runs independently of
      // the fetch above so its own failure never affects the rest.
      checkTaskReminders()
        .catch(() => {})
        .then(() =>
          Promise.all([
            listTaskNotifications({ unreadOnly: true }),
            listInstallationNotifications({ unreadOnly: true }),
            listProductionNotifications({ unreadOnly: true }),
          ])
        )
        .then((result) => {
          if (!result) return;
          const [taskNotifRes, installationNotifRes, productionNotifRes] = result;
          setTaskNotifications(taskNotifRes.items);
          setInstallationNotifications(installationNotifRes.items);
          setProductionNotifications(productionNotifRes.items);
        })
        .catch(() => {
          setTaskNotifications([]);
          setInstallationNotifications([]);
          setProductionNotifications([]);
        });
    });
  }, [t]);

  // Month-over-month delta is only meaningful with at least two trend
  // points; KPIs without a trend history (customers, orders created, win
  // rate) show no delta rather than a fabricated one.
  const revenueDelta = useMemo(() => {
    const trend = executive?.revenue_trend ?? [];
    if (trend.length < 2) return null;
    const prev = parseFloat(trend[trend.length - 2].revenue);
    const curr = parseFloat(trend[trend.length - 1].revenue);
    if (!prev) return null;
    return { pct: ((curr - prev) / prev) * 100, label: t("vsPreviousMonth") };
  }, [executive, t]);

  const profitDelta = useMemo(() => {
    const trend = executive?.revenue_trend ?? [];
    if (trend.length < 2) return null;
    const prev = parseFloat(trend[trend.length - 2].profit);
    const curr = parseFloat(trend[trend.length - 1].profit);
    if (!prev) return null;
    return { pct: ((curr - prev) / prev) * 100, label: t("vsPreviousMonth") };
  }, [executive, t]);

  // Once the initial settle-batch completes (success or partial failure)
  // we're no longer "loading" -- unlike a `=== null` check on any single
  // piece of state, this can't get stuck forever if just one call rejects.
  const loading = !loaded;

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    const key = hour >= 5 && hour < 12 ? "greetingMorning" : hour >= 12 && hour < 18 ? "greetingAfternoon" : "greetingEvening";
    return fullName ? t(key, { name: fullName.split(" ")[0] }) : t("title");
  }, [fullName, t]);

  const orderById = useMemo(() => new Map((orders ?? []).map((o) => [o.id, o])), [orders]);

  // Memoized so re-renders triggered by unrelated state don't re-run these
  // O(n) filters/sorts over the full tasks/orders/installation-jobs arrays.
  const { overdueTasks, dueTodayTasks } = useMemo(() => {
    const list = tasks ?? [];
    const now = Date.now();
    const todayStr = new Date().toDateString();
    return {
      overdueTasks: list.filter((task) => task.due_date && new Date(task.due_date).getTime() < now),
      dueTodayTasks: [...list]
        .filter((task) => task.due_date && new Date(task.due_date).toDateString() === todayStr)
        .sort((a, b) => new Date(a.due_date as string).getTime() - new Date(b.due_date as string).getTime()),
    };
  }, [tasks]);

  const inProductionWorkOrders = useMemo(
    () => (workOrders ?? []).filter((wo) => !WORK_ORDER_TERMINAL_STATUSES.has(wo.status)),
    [workOrders]
  );

  const { installationsTomorrow, upcomingInstallations } = useMemo(() => {
    const activeJobs = (installationJobs ?? []).filter(
      (job) => !INSTALLATION_JOB_TERMINAL_STATUSES.has(job.status) && job.scheduled_date
    );
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowKey = toDateKey(tomorrow);
    return {
      installationsTomorrow: activeJobs.filter((job) => job.scheduled_date === tomorrowKey),
      upcomingInstallations: [...activeJobs]
        .sort((a, b) => (a.scheduled_date as string).localeCompare(b.scheduled_date as string))
        .slice(0, 5),
    };
  }, [installationJobs]);

  const overdueOrders = useMemo(() => {
    const todayKey = toDateKey(new Date());
    return (orders ?? [])
      .filter((order) => !ORDER_TERMINAL_STATUSES.has(order.status))
      .map((order) => {
        let referenceDate: string | null = null;
        if (
          ORDER_PRODUCTION_STAGE_STATUSES.has(order.status) &&
          order.scheduled_production_date &&
          order.scheduled_production_date < todayKey
        ) {
          referenceDate = order.scheduled_production_date;
        } else if (
          ORDER_INSTALLATION_STAGE_STATUSES.has(order.status) &&
          order.scheduled_installation_date &&
          order.scheduled_installation_date < todayKey
        ) {
          referenceDate = order.scheduled_installation_date;
        }
        return referenceDate ? { order, referenceDate } : null;
      })
      .filter((entry): entry is { order: Order; referenceDate: string } => entry !== null)
      .sort((a, b) => a.referenceDate.localeCompare(b.referenceDate));
  }, [orders]);

  // Customer/project names are resolved by id, on demand, for just the
  // records actually rendered below (overdue orders + upcoming
  // installations) -- not from a bulk, page-capped customer/project list,
  // which would miss names for records outside an arbitrary first page on
  // a company with many customers/projects (PROJECT_AUDIT.md B3). Mirrors
  // the same per-id lookup pattern already used on the Orders/Production
  // list pages.
  useEffect(() => {
    const customerIds = new Set<string>();
    const projectIds = new Set<string>();
    overdueOrders.forEach(({ order }) => {
      customerIds.add(order.customer_id);
      projectIds.add(order.project_id);
    });
    upcomingInstallations.forEach((job) => {
      const order = orderById.get(job.order_id);
      if (order) {
        customerIds.add(order.customer_id);
        projectIds.add(order.project_id);
      }
    });

    if (customerIds.size > 0) {
      Promise.all(
        Array.from(customerIds).map((id) =>
          getCustomer(id)
            .then((c) => [id, c.name] as const)
            .catch(() => null)
        )
      ).then((pairs) => {
        const resolved = pairs.filter((p): p is readonly [string, string] => p !== null);
        setCustomerNames(Object.fromEntries(resolved));
      });
    }

    if (projectIds.size > 0) {
      Promise.all(
        Array.from(projectIds).map((id) =>
          getProject(id)
            .then((p) => [id, p.name] as const)
            .catch(() => null)
        )
      ).then((pairs) => {
        const resolved = pairs.filter((p): p is readonly [string, string] => p !== null);
        setProjectNames(Object.fromEntries(resolved));
      });
    }
  }, [overdueOrders, upcomingInstallations, orderById]);

  const notifications = useMemo<NotificationItem[]>(() => {
    const fromTasks = (taskNotifications ?? []).map((n) => ({
      id: `task-${n.id}`,
      title: n.title,
      message: n.message,
      created_at: n.created_at,
      href: `/crm/tasks/${n.task_id}`,
    }));
    const fromInstallation = (installationNotifications ?? []).map((n) => ({
      id: `installation-${n.id}`,
      title: n.title,
      message: n.message,
      created_at: n.created_at,
      href: n.installation_job_id ? `/installation/jobs/${n.installation_job_id}` : "/installation",
    }));
    const fromProduction = (productionNotifications ?? []).map((n) => ({
      id: `production-${n.id}`,
      title: n.title,
      message: n.message,
      created_at: n.created_at,
      href: n.work_order_id ? `/production/${n.work_order_id}` : "/production",
    }));
    return [...fromTasks, ...fromInstallation, ...fromProduction]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 8);
  }, [taskNotifications, installationNotifications, productionNotifications]);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">{greeting}</h1>
          <p className="mt-0.5 text-sm text-text-secondary">
            {t("subtitle")} · {tReports("period_30d")}
          </p>
        </div>
        <div className="flex gap-2">
          {canWriteLeads && (
            <Link href="/crm/leads">
              <Button variant="secondary">{t("captureLead")}</Button>
            </Link>
          )}
          {canWriteCustomers && (
            <Link href="/crm/customers/new">
              <Button>{t("createCustomer")}</Button>
            </Link>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {loading && !error && (
        <div className="flex flex-col gap-8">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <StatCardSkeleton key={i} />
            ))}
          </div>
          <TableSkeleton rows={5} columns={3} />
        </div>
      )}

      {!loading && (
        <>
          {executive && (
            /* Executive snapshot -- the "understand the business in 10
               seconds" surface: big numbers first, operational detail below.
               Independently gated on `executive` so a failure of just this
               one call (of the several the Dashboard fetches in parallel)
               doesn't hide the Inventory/Today sections below, which don't
               depend on it. */
            <section className="flex flex-col gap-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard
                  label={tReports("kpiRevenue")}
                  value={formatNumber(executive.kpis.revenue)}
                  tone="primary"
                  delta={revenueDelta}
                />
                <KpiCard
                  label={tReports("kpiProfit")}
                  value={formatNumber(executive.kpis.profit)}
                  tone="success"
                  hint={tReports("kpiMargin", { pct: executive.kpis.profit_margin_pct })}
                  delta={profitDelta}
                />
                <KpiCard label={tReports("kpiActiveCustomers")} value={formatNumber(executive.kpis.active_customers)} tone="info" />
                <KpiCard label={tReports("kpiOrdersCreated")} value={formatNumber(executive.kpis.orders_created)} tone="neutral" />
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <Card className="p-6 lg:col-span-2">
                  <CardHeader title={tReports("revenueTrend")} />
                  <TrendChart
                    data={executive.revenue_trend.map((r) => ({ month: r.month, revenue: r.revenue, profit: r.profit }))}
                    series={[
                      { key: "revenue", label: tReports("kpiRevenue"), ...TREND_COLORS.revenue },
                      { key: "profit", label: tReports("kpiProfit"), ...TREND_COLORS.profit },
                    ]}
                    areaFill
                    emptyLabel={tReports("noDataPeriod")}
                  />
                </Card>

                <Card className="p-6">
                  <CardHeader title={tReports("ordersByStatus")} />
                  <StatusBarList
                    data={executive.orders_by_status.map((r) => ({ label: tOrders(r.status as Parameters<typeof tOrders>[0]), count: r.count }))}
                    emptyLabel={tReports("noDataPeriod")}
                  />
                </Card>
              </div>
            </section>
          )}

          {inventory && (
            <section className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">
                  {t("sectionInventory")}
                </h2>
                <Link href="/reports/inventory" className="text-sm text-primary hover:underline">
                  {tCommon("viewAll")}
                </Link>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <KpiCard
                  label={tReports("kpiAvailableSlabs")}
                  value={formatNumber(inventory.kpis.available_slabs)}
                  tone="success"
                  hint={`${inventory.kpis.available_area_m2} m²`}
                />
                <KpiCard
                  label={tReports("kpiMaterialsOutOfStock")}
                  value={formatNumber(inventory.kpis.materials_out_of_stock)}
                  tone={inventory.kpis.materials_out_of_stock > 0 ? "danger" : "neutral"}
                />
                <KpiCard
                  label={tReports("kpiWarehousesCount")}
                  value={formatNumber(inventory.kpis.warehouses_count)}
                  tone="neutral"
                />
              </div>
            </section>
          )}

          <h2 className="text-sm font-semibold uppercase tracking-wide text-text-secondary">{t("sectionToday")}</h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label={t("statMeasurementsToday")} value={(measurementsToday ?? []).length} tone="info" />
            <StatCard label={t("statInProduction")} value={inProductionWorkOrders.length} tone="warning" />
            <StatCard label={t("statInstallationsTomorrow")} value={installationsTomorrow.length} tone="info" />
            <StatCard
              label={t("statOverdueWork")}
              value={overdueTasks.length + overdueOrders.length}
              tone="danger"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader
                title={t("sectionTodayTasks")}
                action={
                  <Link href="/crm/tasks" className="text-sm text-primary hover:underline">
                    {tCommon("viewAll")}
                  </Link>
                }
              />
              {dueTodayTasks.length === 0 ? (
                <EmptyState title={t("noTasksToday")} description={t("noTasksTodayDesc")} />
              ) : (
                <ul className="flex flex-col gap-3">
                  {dueTodayTasks.slice(0, 6).map((task) => (
                    <li key={task.id} className="flex items-start gap-3">
                      <TimelineDot tone={task.priority === "urgent" || task.priority === "high" ? "danger" : "warning"} />
                      <div className="flex flex-1 items-center justify-between gap-2">
                        <div>
                          <Link href={`/crm/tasks/${task.id}`} className="font-medium text-primary hover:underline">
                            {task.title}
                          </Link>
                          <p className="text-xs text-text-secondary">
                            {task.due_date ? formatDateTime(task.due_date) : t("noDueDate")}
                          </p>
                        </div>
                        <TaskPriorityBadge priority={task.priority} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader
                title={t("sectionUpcomingInstallations")}
                action={
                  <Link href="/installation/calendar" className="text-sm text-primary hover:underline">
                    {tCommon("viewAll")}
                  </Link>
                }
              />
              {upcomingInstallations.length === 0 ? (
                <EmptyState title={t("noInstallationsUpcoming")} description={t("noInstallationsUpcomingDesc")} />
              ) : (
                <ul className="flex flex-col gap-3">
                  {upcomingInstallations.map((job) => {
                    const order = orderById.get(job.order_id);
                    const customerName = order ? customerNames[order.customer_id] : undefined;
                    const projectName = order ? projectNames[order.project_id] : undefined;
                    return (
                      <li key={job.id} className="flex items-start gap-3">
                        <TimelineDot tone="info" />
                        <div className="flex flex-1 items-center justify-between gap-2">
                          <div>
                            <Link href={`/installation/jobs/${job.id}`} className="font-medium text-primary hover:underline">
                              {projectName ?? job.job_number}
                            </Link>
                            <p className="text-xs text-text-secondary">
                              {customerName ? `${customerName} · ` : ""}
                              {job.scheduled_date ? t("scheduledOn", { date: formatDate(job.scheduled_date) }) : t("noDueDate")}
                            </p>
                          </div>
                          <InstallationJobStatusBadge status={job.status} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title={t("sectionOverdueProjects")} />
              {overdueOrders.length === 0 ? (
                <EmptyState title={t("noOverdueProjects")} description={t("noOverdueProjectsDesc")} />
              ) : (
                <ul className="flex flex-col gap-3">
                  {overdueOrders.slice(0, 6).map(({ order, referenceDate }) => {
                    const customerName = customerNames[order.customer_id];
                    const days = daysBetween(new Date(referenceDate), new Date());
                    return (
                      <li key={order.id} className="flex items-start gap-3">
                        <TimelineDot tone="danger" />
                        <div className="flex flex-1 items-center justify-between gap-2">
                          <div>
                            <Link href={`/orders/${order.id}`} className="font-medium text-primary hover:underline">
                              {projectNames[order.project_id] ?? order.order_number}
                            </Link>
                            <p className="text-xs text-text-secondary">
                              {customerName ? `${customerName} · ` : ""}
                              {t("overdueBy", { days })}
                            </p>
                          </div>
                          <OrderStatusBadge status={order.status} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title={t("sectionNotifications")} />
              {notifications.length === 0 ? (
                <EmptyState title={t("noNotifications")} />
              ) : (
                <ul className="flex flex-col gap-3">
                  {notifications.map((n) => (
                    <li key={n.id} className="flex items-start gap-3">
                      <TimelineDot tone="info" />
                      <div>
                        <Link href={n.href} className="text-sm font-medium text-primary hover:underline">
                          {n.title}
                        </Link>
                        <p className="text-xs text-text-secondary">{n.message}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card>
            <CardHeader
              title={t("sectionRecentInquiries")}
              action={
                <Link href="/crm/leads" className="text-sm text-primary hover:underline">
                  {tCommon("viewAll")}
                </Link>
              }
            />
            {(leads ?? []).length === 0 ? (
              <EmptyState title={t("noInquiriesYet")} description={t("noInquiriesYetDesc")} />
            ) : (
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 z-10 border-b border-border bg-bg text-text-secondary">
                    <tr>
                      <th className="px-4 py-2 font-medium">{t("tableName")}</th>
                      <th className="px-4 py-2 font-medium">{t("tableChannel")}</th>
                      <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                      <th className="px-4 py-2 font-medium">{t("tableCaptured")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(leads ?? []).map((lead) => (
                      <tr key={lead.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-2 font-medium text-text-primary">{lead.full_name}</td>
                        <td className="px-4 py-2">
                          <Badge tone="info">{channelLabel(lead.source_channel)}</Badge>
                        </td>
                        <td className="px-4 py-2">
                          <LeadStatusBadge status={lead.status} />
                        </td>
                        <td className="px-4 py-2 text-text-secondary">{formatDate(lead.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
