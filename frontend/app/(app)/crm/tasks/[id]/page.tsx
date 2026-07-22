"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  deleteTask,
  getCustomer,
  getTask,
  listTaskSeries,
  updateTask,
  updateTaskStatus,
} from "@/lib/api/crm";
import { listCompanyUsers } from "@/lib/api/companies";
import { TASK_PRIORITIES, type CompanyUser, type Task } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TaskPriorityBadge, TaskStatusBadge } from "@/components/ui/badge";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime, fromDatetimeLocalValue, toDatetimeLocalValue } from "@/lib/format";

const inputClasses =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary";

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const t = useTranslations("tasks");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const confirm = useConfirm();
  const toast = useToast();

  const [task, setTask] = useState<Task | null>(null);
  const [series, setSeries] = useState<Task[] | null>(null);
  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [relatedCustomerName, setRelatedCustomerName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    priority: "medium",
    due_date: "",
    remind_at: "",
    assigned_to: "",
    tags: "",
  });

  const reload = useCallback(async () => {
    const fetched = await getTask(id);
    setTask(fetched);
    setForm({
      title: fetched.title,
      description: fetched.description ?? "",
      priority: fetched.priority,
      due_date: toDatetimeLocalValue(fetched.due_date),
      remind_at: toDatetimeLocalValue(fetched.remind_at),
      assigned_to: fetched.assigned_to ?? "",
      tags: fetched.tags.join(", "),
    });

    if (fetched.is_recurring || fetched.series_id) {
      setSeries((await listTaskSeries(id)).items);
    } else {
      setSeries(null);
    }

    if (fetched.related_entity_type === "customer" && fetched.related_entity_id) {
      getCustomer(fetched.related_entity_id).then((c) => setRelatedCustomerName(c.name)).catch(() => {});
    } else {
      setRelatedCustomerName(null);
    }

    setLoading(false);
  }, [id]);

  useEffect(() => { reload(); }, [reload]);
  useEffect(() => { listCompanyUsers().then(setUsers).catch(() => {}); }, []);

  const userName = (userId: string | null) =>
    userId ? users.find((u) => u.id === userId)?.full_name ?? userId : tCommon("dash");

  async function handleStatus(status: string, reason?: string) {
    setBusy(true);
    try {
      await updateTaskStatus(id, status, reason);
      setCancelMode(false);
      await reload();
      toast.success(t("statusUpdated"));
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    setBusy(true);
    try {
      await updateTask(id, {
        title: form.title,
        description: form.description || undefined,
        priority: form.priority,
        due_date: fromDatetimeLocalValue(form.due_date),
        remind_at: fromDatetimeLocalValue(form.remind_at),
        assigned_to: form.assigned_to || undefined,
        tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      });
      setEditMode(false);
      await reload();
      toast.success(t("taskUpdated"));
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!(await confirm(t("confirmDelete")))) return;
    try {
      await deleteTask(id);
      router.push("/crm/tasks");
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  if (loading || !task) return <TableSkeleton rows={5} columns={3} />;

  const isTerminal = task.status === "done" || task.status === "cancelled";

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("tasks"), href: "/crm/tasks" }, { label: task.title }]} />

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-text-primary">{task.title}</h1>
            <TaskStatusBadge status={task.status} />
            <TaskPriorityBadge priority={task.priority} />
            {task.is_recurring && <span className="text-xs text-text-secondary">↻ {t(`recurrence_${task.recurrence_rule}` as Parameters<typeof t>[0])}</span>}
          </div>
          {task.related_entity_type === "customer" && task.related_entity_id && (
            <p className="mt-1 text-xs text-text-secondary">
              {t("relatedTo")}:{" "}
              <Link href={`/crm/customers/${task.related_entity_id}`} className="text-primary hover:underline">
                {relatedCustomerName ?? tCommon("loading")}
              </Link>
            </p>
          )}
        </div>
        {!isTerminal && (
          <div className="flex flex-wrap justify-end gap-2">
            {task.status === "pending" && (
              <Button variant="secondary" onClick={() => handleStatus("in_progress")} disabled={busy}>
                {t("start")}
              </Button>
            )}
            {task.status === "in_progress" && (
              <Button variant="secondary" onClick={() => handleStatus("pending")} disabled={busy}>
                {t("backToPending")}
              </Button>
            )}
            <Button onClick={() => handleStatus("done")} disabled={busy}>
              {busy ? t("saving") : t("complete")}
            </Button>
            <Button variant="destructive" onClick={() => setCancelMode(!cancelMode)}>
              {t("cancelTask")}
            </Button>
          </div>
        )}
      </div>

      {cancelMode && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="mb-2 text-sm font-medium text-danger">{t("cancelReason")}</p>
          <textarea
            className={`${inputClasses} mb-2 w-full`}
            rows={2}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <div className="flex gap-2">
            <Button onClick={() => handleStatus("cancelled", cancelReason || undefined)} disabled={busy}>
              {t("cancelTask")}
            </Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text-primary">{t("details")}</h2>
          <div className="flex gap-3">
            {!isTerminal && (
              <button className="text-xs text-primary hover:underline" onClick={() => (editMode ? handleSave() : setEditMode(true))}>
                {editMode ? tCommon("save") : tCommon("edit")}
              </button>
            )}
            <button className="text-xs text-danger hover:underline" onClick={handleDelete}>
              {tCommon("delete")}
            </button>
          </div>
        </div>

        {editMode ? (
          <div className="flex flex-col gap-3 text-sm">
            <TextField label={t("taskTitle")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <TextAreaField label={t("description")} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <SelectField label={t("priority")} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {TASK_PRIORITIES.map((p) => (
                  <option key={p} value={p}>{t(`priority_${p}` as Parameters<typeof t>[0])}</option>
                ))}
              </SelectField>
              <SelectField label={t("assignee")} value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })}>
                <option value="">{t("unassigned")}</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </SelectField>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField label={t("dueDate")} type="datetime-local" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
              <TextField label={t("remindAt")} type="datetime-local" value={form.remind_at} onChange={(e) => setForm({ ...form, remind_at: e.target.value })} />
            </div>
            <TextField label={t("tags")} value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder={t("tagsPlaceholder")} />
          </div>
        ) : (
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-text-secondary">{t("description")}</dt>
              <dd className="text-text-primary">{task.description ?? tCommon("dash")}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">{t("assignee")}</dt>
              <dd className="text-text-primary">{userName(task.assigned_to)}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">{t("dueDate")}</dt>
              <dd className="text-text-primary">{task.due_date ? formatDateTime(task.due_date) : tCommon("dash")}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">{t("remindAt")}</dt>
              <dd className="text-text-primary">{task.remind_at ? formatDateTime(task.remind_at) : tCommon("dash")}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">{t("tags")}</dt>
              <dd className="text-text-primary">{task.tags.length > 0 ? task.tags.join(", ") : tCommon("dash")}</dd>
            </div>
            {task.status === "cancelled" && (
              <div>
                <dt className="text-xs text-text-secondary">{t("cancelReason")}</dt>
                <dd className="text-text-primary">{task.cancelled_reason ?? tCommon("dash")}</dd>
              </div>
            )}
          </dl>
        )}
      </Card>

      {series && series.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <div className="bg-primary px-4 py-3 text-white">
            <h2 className="font-semibold">{t("series")}</h2>
          </div>
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">{t("tableDueDate")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
              </tr>
            </thead>
            <tbody>
              {series.map((occurrence) => (
                <tr key={occurrence.id} className="border-t border-border">
                  <td className="px-4 py-2">
                    {occurrence.id === task.id ? (
                      <span className="font-medium text-text-primary">
                        {occurrence.due_date ? formatDateTime(occurrence.due_date) : tCommon("dash")} ({t("thisTask")})
                      </span>
                    ) : (
                      <Link href={`/crm/tasks/${occurrence.id}`} className="text-primary hover:underline">
                        {occurrence.due_date ? formatDateTime(occurrence.due_date) : tCommon("dash")}
                      </Link>
                    )}
                  </td>
                  <td className="px-4 py-2"><TaskStatusBadge status={occurrence.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </Card>
      )}
    </div>
  );
}
