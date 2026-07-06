"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { checkTaskReminders, listCustomers, listLeads, listTaskNotifications, listTasks } from "@/lib/api/crm";
import { me } from "@/lib/api/auth";
import { CUSTOMER_STATUSES, type Customer, type Lead, type Task, type TaskNotification } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatusBarList } from "@/components/ui/charts";
import { Badge, CustomerStatusBadge, LeadStatusBadge, TaskPriorityBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { formatDate, formatDateTime } from "@/lib/format";
import { useCustomerStatusLabel, useLeadChannelLabel } from "@/lib/i18n/hooks";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const channelLabel = useLeadChannelLabel();
  const statusLabel = useCustomerStatusLabel();
  const [fullName, setFullName] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [myTasks, setMyTasks] = useState<Task[] | null>(null);
  const [notifications, setNotifications] = useState<TaskNotification[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      me(),
      listCustomers({ includeArchived: true, limit: 100 }),
      listLeads({ limit: 100 }),
    ])
      .then(([profile, customerRes, leadRes]) => {
        setFullName(profile.full_name);
        setRole(profile.role);
        setCustomers(customerRes.items);
        setLeads(leadRes.items);

        // Surfaces newly-due reminders/overdue tasks the moment the
        // Dashboard loads -- see checkTaskReminders' doc comment for why
        // this is a pull rather than a scheduled push.
        checkTaskReminders()
          .catch(() => {})
          .then(() =>
            Promise.all([
              listTasks({ assignedTo: profile.id, excludeTerminal: true, sort: "due_date", limit: 100 }),
              listTaskNotifications({ unreadOnly: true }),
            ])
          )
          .then((result) => {
            if (!result) return;
            const [taskRes, notificationRes] = result;
            setMyTasks(taskRes.items);
            setNotifications(notificationRes.items);
          })
          .catch(() => {
            setMyTasks([]);
            setNotifications([]);
          });
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  const loading = customers === null || leads === null;

  // Memoized so re-renders triggered by unrelated state (locale/theme
  // toggles, sibling component updates) don't re-run these O(n) filters/
  // sorts over the full customers/leads/tasks arrays every time.
  const { overdueTasks, dueTodayTasks, upcomingTasks } = useMemo(() => {
    const tasks = myTasks ?? [];
    const now = Date.now();
    const today = new Date();
    return {
      overdueTasks: tasks.filter((task) => task.due_date && new Date(task.due_date).getTime() < now),
      dueTodayTasks: tasks.filter((task) => task.due_date && new Date(task.due_date).toDateString() === today.toDateString()),
      upcomingTasks: [...tasks]
        .sort((a, b) => {
          if (!a.due_date) return 1;
          if (!b.due_date) return -1;
          return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
        })
        .slice(0, 5),
    };
  }, [myTasks]);

  const activeCustomers = useMemo(() => customers?.filter((c) => c.deleted_at === null) ?? [], [customers]);

  const { customersByStatus, newInquiries, inProduction, lostCustomers, recentCustomers } = useMemo(() => {
    return {
      customersByStatus: CUSTOMER_STATUSES.map((status) => ({
        status,
        count: activeCustomers.filter((c) => c.status === status).length,
      })),
      newInquiries: activeCustomers.filter((c) => c.status === "new_inquiry").length,
      inProduction: activeCustomers.filter(
        (c) => c.status === "in_production" || c.status === "installation_scheduled"
      ).length,
      lostCustomers: activeCustomers.filter((c) => c.status === "lost").length,
      recentCustomers: [...activeCustomers]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5),
    };
  }, [activeCustomers]);

  const recentLeads = useMemo(
    () =>
      [...(leads ?? [])]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5),
    [leads]
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">
            {fullName ? t("welcomeBack", { name: fullName.split(" ")[0] }) : t("title")}
          </h1>
          <p className="text-sm text-text-secondary">{role ? t("signedInAs", { role }) : t("overview")}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/crm/leads">
            <Button variant="secondary">{t("captureLead")}</Button>
          </Link>
          <Link href="/crm/customers/new">
            <Button>{t("createCustomer")}</Button>
          </Link>
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {loading && !error && (
        <div className="flex flex-col gap-6">
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
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label={t("statActiveCustomers")} value={activeCustomers.length} tone="primary" />
            <StatCard label={statusLabel("new_inquiry")} value={newInquiries} tone="info" />
            <StatCard label={t("statInProduction")} value={inProduction} tone="warning" />
            <StatCard label={statusLabel("lost")} value={lostCustomers} tone="danger" />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label={t("statMyOpenTasks")} value={(myTasks ?? []).length} tone="primary" />
            <StatCard label={t("statOverdueTasks")} value={overdueTasks.length} tone="danger" />
            <StatCard label={t("statDueToday")} value={dueTodayTasks.length} tone="warning" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader
                title={t("myTasks")}
                action={
                  <Link href="/crm/tasks" className="text-sm text-primary hover:underline">
                    {tCommon("viewAll")}
                  </Link>
                }
              />
              {upcomingTasks.length === 0 ? (
                <EmptyState title={t("noTasksYet")} description={t("noTasksDesc")} />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {upcomingTasks.map((task) => (
                    <li key={task.id} className="flex items-center justify-between py-2">
                      <div>
                        <Link href={`/crm/tasks/${task.id}`} className="font-medium text-primary hover:underline">
                          {task.title}
                        </Link>
                        <p className="text-xs text-text-secondary">
                          {task.due_date ? formatDateTime(task.due_date) : t("noDueDate")}
                        </p>
                      </div>
                      <TaskPriorityBadge priority={task.priority} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title={t("notifications")} />
              {(notifications ?? []).length === 0 ? (
                <EmptyState title={t("noNotifications")} />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {(notifications ?? []).map((notification) => (
                    <li key={notification.id} className="py-2">
                      <Link href={`/crm/tasks/${notification.task_id}`} className="text-sm font-medium text-primary hover:underline">
                        {notification.title}
                      </Link>
                      <p className="text-xs text-text-secondary">{notification.message}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader
                title={t("recentCustomers")}
                action={
                  <Link href="/crm/customers" className="text-sm text-primary hover:underline">
                    {tCommon("viewAll")}
                  </Link>
                }
              />
              {recentCustomers.length === 0 ? (
                <EmptyState title={t("noCustomersYet")} description={t("noCustomersDesc")} />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {recentCustomers.map((customer) => (
                    <li key={customer.id} className="flex items-center justify-between py-2">
                      <div>
                        <Link href={`/crm/customers/${customer.id}`} className="font-medium text-primary hover:underline">
                          {customer.name}
                        </Link>
                        <p className="text-xs text-text-secondary">
                          {t("createdOn", { date: formatDate(customer.created_at) })}
                        </p>
                      </div>
                      <CustomerStatusBadge status={customer.status} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title={t("customersByStatus")} />
              <StatusBarList
                data={customersByStatus.map(({ status, count }) => ({ label: statusLabel(status), count }))}
                emptyLabel={t("noCustomersYet")}
              />
            </Card>
          </div>

          <Card>
            <CardHeader
              title={t("recentLeads")}
              action={
                <Link href="/crm/leads" className="text-sm text-primary hover:underline">
                  {tCommon("viewAll")}
                </Link>
              }
            />
            {recentLeads.length === 0 ? (
              <EmptyState title={t("noLeadsYet")} description={t("noLeadsDesc")} />
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
                    {recentLeads.map((lead) => (
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
