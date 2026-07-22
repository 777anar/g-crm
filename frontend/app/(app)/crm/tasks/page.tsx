"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { checkTaskReminders, listTasks } from "@/lib/api/crm";
import { listCompanyUsers } from "@/lib/api/companies";
import { TASK_PRIORITIES, TASK_STATUSES, type CompanyUser, type Task } from "@/lib/types";
import { TaskPriorityBadge, TaskStatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SalesSectionTabs } from "@/components/sales-section-tabs";
import { TableSkeleton } from "@/components/ui/skeleton";
import {
  ColumnResizeHandle,
  ColumnVisibilityMenu,
  SavedFiltersBar,
  stickyTheadClass,
  tableScrollShellClass,
  useColumnVisibility,
  useResizableColumns,
  useSavedFilters,
} from "@/components/ui/data-table";
import { SortableHeader } from "@/components/ui/sortable-header";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";

const TABLE_ID = "crm-tasks";

type TasksFilters = {
  statusFilter: string;
  priorityFilter: string;
  assigneeFilter: string;
  tagFilter: string;
  excludeTerminal: boolean;
  search: string;
  sort: string;
};

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
  const searchInputRef = useRef<HTMLInputElement>(null);

  useListShortcuts({ searchInputRef, onCreate: () => router.push("/crm/tasks/new") });

  const columnDefs = [
    { id: "title", label: t("tableTitle") },
    { id: "status", label: t("tableStatus") },
    { id: "priority", label: t("tablePriority") },
    { id: "assignee", label: t("tableAssignee") },
    { id: "dueDate", label: t("tableDueDate") },
    { id: "tags", label: t("tableTags") },
  ];
  const { isVisible, toggle, reset } = useColumnVisibility(TABLE_ID, columnDefs);
  const { widthOf, startResize } = useResizableColumns(TABLE_ID, {
    title: 220,
    status: 130,
    priority: 130,
    assignee: 160,
    dueDate: 160,
    tags: 160,
  });
  const savedFilters = useSavedFilters<TasksFilters>(TABLE_ID);

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

  function applyFilters(filters: TasksFilters) {
    setStatusFilter(filters.statusFilter);
    setPriorityFilter(filters.priorityFilter);
    setAssigneeFilter(filters.assigneeFilter);
    setTagFilter(filters.tagFilter);
    setExcludeTerminal(filters.excludeTerminal);
    setSearchInput(filters.search);
    setSort(filters.sort);
  }

  return (
    <div className="flex flex-col gap-4">
      <SalesSectionTabs />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
          <p className="text-sm text-text-secondary">{t("subtitle")}</p>
        </div>
        <Link href="/crm/tasks/new">
          <Button>{t("newTask")}</Button>
        </Link>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={searchInputRef}
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{tCommon("allStatuses")}</option>
            {TASK_STATUSES.map((s) => (
              <option key={s} value={s}>{t(s as Parameters<typeof t>[0])}</option>
            ))}
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          >
            <option value="">{t("allPriorities")}</option>
            {TASK_PRIORITIES.map((p) => (
              <option key={p} value={p}>{t(`priority_${p}` as Parameters<typeof t>[0])}</option>
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
        <ColumnVisibilityMenu columns={columnDefs} isVisible={isVisible} toggle={toggle} reset={reset} />
      </div>

      <SavedFiltersBar
        presets={savedFilters.presets}
        onApply={applyFilters}
        onSave={(name) =>
          savedFilters.save(name, {
            statusFilter,
            priorityFilter,
            assigneeFilter,
            tagFilter,
            excludeTerminal,
            search: searchInput,
            sort,
          })
        }
        onRemove={savedFilters.remove}
      />

      {error && <p className="text-sm text-danger">{error}</p>}

      {tasks === null && !error && <TableSkeleton rows={5} columns={5} />}

      {visibleTasks && visibleTasks.length === 0 && (
        <EmptyState title={t("noTasksYet")} description={t("noTasksDesc")} />
      )}

      {visibleTasks && visibleTasks.length > 0 && (
        <div className={tableScrollShellClass}>
          <table className="w-full text-left text-sm">
            <thead className={stickyTheadClass}>
              <tr>
                {isVisible("title") && (
                  <SortableHeader
                    field="title"
                    label={t("tableTitle")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("title")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("title")} />}
                  />
                )}
                {isVisible("status") && (
                  <SortableHeader
                    field="status"
                    label={t("tableStatus")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("status")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("status")} />}
                  />
                )}
                {isVisible("priority") && (
                  <SortableHeader
                    field="priority"
                    label={t("tablePriority")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("priority")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("priority")} />}
                  />
                )}
                {isVisible("assignee") && (
                  <th className="relative px-4 py-2 font-medium" style={{ width: widthOf("assignee") }}>
                    {t("tableAssignee")}
                    <ColumnResizeHandle onMouseDown={startResize("assignee")} />
                  </th>
                )}
                {isVisible("dueDate") && (
                  <SortableHeader
                    field="due_date"
                    label={t("tableDueDate")}
                    sort={sort}
                    onSortChange={setSort}
                    width={widthOf("dueDate")}
                    resizeHandle={<ColumnResizeHandle onMouseDown={startResize("dueDate")} />}
                  />
                )}
                {isVisible("tags") && (
                  <th className="px-4 py-2 font-medium" style={{ width: widthOf("tags") }}>
                    {t("tableTags")}
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {visibleTasks.map((task) => (
                <tr
                  key={task.id}
                  onClick={() => router.push(`/crm/tasks/${task.id}`)}
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-bg"
                >
                  {isVisible("title") && (
                    <td className="px-4 py-2 font-medium text-text-primary">
                      {task.title}
                      {task.is_recurring && <span className="ml-1 text-xs text-text-secondary">↻</span>}
                    </td>
                  )}
                  {isVisible("status") && (
                    <td className="px-4 py-2"><TaskStatusBadge status={task.status} /></td>
                  )}
                  {isVisible("priority") && (
                    <td className="px-4 py-2"><TaskPriorityBadge priority={task.priority} /></td>
                  )}
                  {isVisible("assignee") && (
                    <td className="px-4 py-2 text-text-secondary">{userName(task.assigned_to)}</td>
                  )}
                  {isVisible("dueDate") && (
                    <td className="px-4 py-2 text-text-secondary">
                      {task.due_date ? formatDateTime(task.due_date) : tCommon("dash")}
                    </td>
                  )}
                  {isVisible("tags") && (
                    <td className="px-4 py-2 text-text-secondary">
                      {task.tags.length > 0 ? task.tags.join(", ") : tCommon("dash")}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
