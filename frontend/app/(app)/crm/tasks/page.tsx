"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { checkTaskReminders, listTasks } from "@/lib/api/crm";
import { listCompanyUsers } from "@/lib/api/companies";
import { TASK_PRIORITIES, TASK_STATUSES, type CompanyUser, type Task } from "@/lib/types";
import { TaskPriorityBadge, TaskStatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

export default function TasksPage() {
  const t = useTranslations("tasks");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [excludeTerminal, setExcludeTerminal] = useState(true);
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("due_date");
  const [error, setError] = useState<string | null>(null);
  const search = useDebouncedValue(searchInput, 250);

  const load = useCallback(() => {
    listTasks({
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
      assignedTo: assigneeFilter || undefined,
      excludeTerminal,
      search: search || undefined,
      sort,
      limit: 100,
    })
      .then((r) => setTasks(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [statusFilter, priorityFilter, assigneeFilter, excludeTerminal, search, sort, t]);

  useEffect(() => {
    setTasks(null);
    load();
  }, [load]);

  useEffect(() => {
    listCompanyUsers().then(setUsers).catch(() => {});
    // Surfaces any newly-due reminders/overdue tasks as notifications the
    // moment the user opens the Tasks page -- see checkTaskReminders' doc
    // comment for why this is a pull rather than a scheduled push.
    checkTaskReminders().catch(() => {});
  }, []);

  const userName = (id: string | null) => (id ? users.find((u) => u.id === id)?.full_name ?? id : tCommon("dash"));

  const visibleTasks = tagFilter
    ? tasks?.filter((task) => task.tags.some((tag) => tag.toLowerCase().includes(tagFilter.toLowerCase())))
    : tasks;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
          <p className="text-sm text-text-secondary">{t("subtitle")}</p>
        </div>
        <Link href="/crm/tasks/new">
          <Button>{t("newTask")}</Button>
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={tCommon("search")}
          className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        >
          <option value="">{tCommon("allStatuses")}</option>
          {TASK_STATUSES.map((s) => (
            <option key={s} value={s}>{t(s as any)}</option>
          ))}
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        >
          <option value="">{t("allPriorities")}</option>
          {TASK_PRIORITIES.map((p) => (
            <option key={p} value={p}>{t(`priority_${p}` as any)}</option>
          ))}
        </select>
        <select
          value={assigneeFilter}
          onChange={(e) => setAssigneeFilter(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        >
          <option value="">{t("allAssignees")}</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>{u.full_name}</option>
          ))}
        </select>
        <input
          type="text"
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          placeholder={t("filterByTag")}
          className="w-32 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
        >
          <option value="due_date">{t("sortDueDate")}</option>
          <option value="-created_at">{t("sortNewest")}</option>
          <option value="priority">{t("sortPriority")}</option>
          <option value="title">{t("sortTitle")}</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-text-secondary">
          <input type="checkbox" checked={excludeTerminal} onChange={(e) => setExcludeTerminal(e.target.checked)} />
          {t("hideClosed")}
        </label>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {tasks === null && !error && <TableSkeleton rows={5} columns={5} />}

      {visibleTasks && visibleTasks.length === 0 && (
        <EmptyState title={t("noTasksYet")} description={t("noTasksDesc")} />
      )}

      {visibleTasks && visibleTasks.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("tableTitle")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                <th className="px-4 py-2 font-medium">{t("tablePriority")}</th>
                <th className="px-4 py-2 font-medium">{t("tableAssignee")}</th>
                <th className="px-4 py-2 font-medium">{t("tableDueDate")}</th>
                <th className="px-4 py-2 font-medium">{t("tableTags")}</th>
              </tr>
            </thead>
            <tbody>
              {visibleTasks.map((task) => (
                <tr
                  key={task.id}
                  onClick={() => router.push(`/crm/tasks/${task.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  <td className="px-4 py-2 font-medium text-text-primary">
                    {task.title}
                    {task.is_recurring && <span className="ml-1 text-xs text-text-secondary">↻</span>}
                  </td>
                  <td className="px-4 py-2"><TaskStatusBadge status={task.status} /></td>
                  <td className="px-4 py-2"><TaskPriorityBadge priority={task.priority} /></td>
                  <td className="px-4 py-2 text-text-secondary">{userName(task.assigned_to)}</td>
                  <td className="px-4 py-2 text-text-secondary">
                    {task.due_date ? formatDateTime(task.due_date) : tCommon("dash")}
                  </td>
                  <td className="px-4 py-2 text-text-secondary">
                    {task.tags.length > 0 ? task.tags.join(", ") : tCommon("dash")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
