"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { createTask } from "@/lib/api/crm";
import { listCompanyUsers } from "@/lib/api/companies";
import { TASK_PRIORITIES, TASK_RECURRENCE_RULES, type CompanyUser } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { fromDatetimeLocalValue } from "@/lib/format";

export default function NewTaskPage() {
  const router = useRouter();
  const t = useTranslations("tasks");
  const tCommon = useTranslations("common");
  const toast = useToast();

  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<string>("medium");
  const [dueDate, setDueDate] = useState("");
  const [remindAt, setRemindAt] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [tags, setTags] = useState("");
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrenceRule, setRecurrenceRule] = useState<string>("weekly");
  const [recurrenceInterval, setRecurrenceInterval] = useState("1");
  const [recurrenceEndDate, setRecurrenceEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listCompanyUsers().then(setUsers).catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const task = await createTask({
        title,
        description: description || undefined,
        priority,
        due_date: fromDatetimeLocalValue(dueDate),
        remind_at: fromDatetimeLocalValue(remindAt),
        assigned_to: assignedTo || undefined,
        tags: tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        is_recurring: isRecurring,
        recurrence_rule: isRecurring ? recurrenceRule : undefined,
        recurrence_interval: isRecurring ? Number(recurrenceInterval) || 1 : undefined,
        recurrence_end_date: isRecurring ? recurrenceEndDate || undefined : undefined,
      });
      toast.success(t("taskCreated"));
      router.push(`/crm/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Card>
        <CardHeader title={t("newTask")} />
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <TextField label={t("taskTitle")} value={title} onChange={(e) => setTitle(e.target.value)} required autoFocus />
          <TextAreaField label={t("description")} value={description} onChange={(e) => setDescription(e.target.value)} />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectField label={t("priority")} value={priority} onChange={(e) => setPriority(e.target.value)}>
              {TASK_PRIORITIES.map((p) => (
                <option key={p} value={p}>{t(`priority_${p}` as any)}</option>
              ))}
            </SelectField>
            <SelectField label={t("assignee")} value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)}>
              <option value="">{t("unassigned")}</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name}</option>
              ))}
            </SelectField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField
              label={t("dueDate")}
              type="datetime-local"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
            <TextField
              label={t("remindAt")}
              type="datetime-local"
              value={remindAt}
              onChange={(e) => setRemindAt(e.target.value)}
            />
          </div>

          <TextField label={t("tags")} value={tags} onChange={(e) => setTags(e.target.value)} placeholder={t("tagsPlaceholder")} />

          <label className="flex items-center gap-2 text-sm text-text-primary">
            <input type="checkbox" checked={isRecurring} onChange={(e) => setIsRecurring(e.target.checked)} />
            {t("isRecurring")}
          </label>

          {isRecurring && (
            <div className="grid grid-cols-1 gap-4 rounded-md border border-border p-3 sm:grid-cols-3">
              <SelectField
                label={t("recurrenceRule")}
                value={recurrenceRule}
                onChange={(e) => setRecurrenceRule(e.target.value)}
              >
                {TASK_RECURRENCE_RULES.map((r) => (
                  <option key={r} value={r}>{t(`recurrence_${r}` as any)}</option>
                ))}
              </SelectField>
              <TextField
                label={t("recurrenceInterval")}
                type="number"
                min={1}
                value={recurrenceInterval}
                onChange={(e) => setRecurrenceInterval(e.target.value)}
              />
              <TextField
                label={t("recurrenceEndDate")}
                type="date"
                value={recurrenceEndDate}
                onChange={(e) => setRecurrenceEndDate(e.target.value)}
              />
            </div>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => router.back()}>
              {tCommon("cancel")}
            </Button>
            <Button type="submit" loading={submitting} disabled={!title.trim() || (isRecurring && !dueDate)}>
              {t("newTask")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
