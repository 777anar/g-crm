"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { createTemplate, listTemplates, updateTemplate } from "@/lib/api/communication";
import { CHANNEL_TYPES, type MessageTemplate } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { ChannelTypeBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";

const emptyForm = { name: "", body: "", channel_type: "", shortcut: "" };

export default function TemplatesPage() {
  const t = useTranslations("communication");
  const tCommon = useTranslations("common");

  const [templates, setTemplates] = useState<MessageTemplate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(() => {
    listTemplates()
      .then((r) => setTemplates(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.body.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      await createTemplate({
        name: form.name.trim(),
        body: form.body.trim(),
        channel_type: form.channel_type || undefined,
        shortcut: form.shortcut || undefined,
      });
      setForm(emptyForm);
      load();
    } catch (err) {
      setCreateError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleActive(template: MessageTemplate) {
    await updateTemplate(template.id, { is_active: !template.is_active });
    load();
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("templatesTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("templatesSubtitle")}</p>
      </div>

      <Card>
        <form onSubmit={handleCreate} className="flex flex-col gap-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <TextField
              label={t("templateName")}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <SelectField
              label={t("channelType")}
              value={form.channel_type}
              onChange={(e) => setForm({ ...form, channel_type: e.target.value })}
            >
              <option value="">{t("anyChannel")}</option>
              {CHANNEL_TYPES.map((ct) => (
                <option key={ct} value={ct}>{t(`channel_${ct}` as Parameters<typeof t>[0])}</option>
              ))}
            </SelectField>
            <TextField
              label={t("shortcut")}
              value={form.shortcut}
              onChange={(e) => setForm({ ...form, shortcut: e.target.value })}
              placeholder={t("shortcutPlaceholder")}
            />
          </div>
          <TextAreaField
            label={t("templateBody")}
            value={form.body}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
          />
          <div className="flex justify-end">
            <Button type="submit" disabled={creating || !form.name.trim() || !form.body.trim()}>
              {creating ? t("creating") : t("addTemplate")}
            </Button>
          </div>
        </form>
        {createError && <p className="mt-2 text-sm text-danger">{createError}</p>}
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}
      {templates === null && !error && <TableSkeleton rows={3} columns={3} />}
      {templates && templates.length === 0 && (
        <EmptyState title={t("noTemplatesYet")} description={t("noTemplatesDesc")} />
      )}

      <div className="flex flex-col gap-2">
        {templates?.map((template) => (
          <Card key={template.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-text-primary">{template.name}</p>
                  {template.channel_type ? (
                    <ChannelTypeBadge channelType={template.channel_type} />
                  ) : (
                    <span className="text-xs text-text-secondary">{t("anyChannel")}</span>
                  )}
                  {template.shortcut && <span className="text-xs text-text-secondary">/{template.shortcut}</span>}
                </div>
                <p className="mt-1 text-sm text-text-secondary">{template.body}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className={`text-xs font-medium ${template.is_active ? "text-success" : "text-text-secondary"}`}>
                  {template.is_active ? t("active") : t("inactive")}
                </span>
                <Button variant="secondary" onClick={() => handleToggleActive(template)}>
                  {template.is_active ? tCommon("deactivate") : tCommon("activate")}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
