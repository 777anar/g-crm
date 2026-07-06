"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { createChannel, listChannels, updateChannel } from "@/lib/api/communication";
import { CHANNEL_TYPES, type Channel } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SelectField, TextField } from "@/components/ui/field";
import { ChannelTypeBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";

const emptyForm = { channel_type: "whatsapp", display_name: "", identifier: "" };

export default function ChannelsPage() {
  const t = useTranslations("communication");
  const tCommon = useTranslations("common");

  const [channels, setChannels] = useState<Channel[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(() => {
    listChannels()
      .then((r) => setChannels(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.display_name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      await createChannel({
        channel_type: form.channel_type,
        display_name: form.display_name.trim(),
        identifier: form.identifier || undefined,
      });
      setForm(emptyForm);
      load();
    } catch (err) {
      setCreateError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleActive(channel: Channel) {
    await updateChannel(channel.id, { is_active: !channel.is_active });
    load();
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("channelsTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("channelsSubtitle")}</p>
      </div>

      <Card>
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-3 md:grid-cols-4 md:items-end">
          <SelectField
            label={t("channelType")}
            value={form.channel_type}
            onChange={(e) => setForm({ ...form, channel_type: e.target.value })}
          >
            {CHANNEL_TYPES.map((ct) => (
              <option key={ct} value={ct}>{t(`channel_${ct}` as any)}</option>
            ))}
          </SelectField>
          <TextField
            label={t("displayName")}
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            placeholder={t("displayNamePlaceholder")}
          />
          <TextField
            label={t("identifier")}
            value={form.identifier}
            onChange={(e) => setForm({ ...form, identifier: e.target.value })}
            placeholder={t("identifierPlaceholder")}
          />
          <Button type="submit" disabled={creating || !form.display_name.trim()}>
            {creating ? t("creating") : t("addChannel")}
          </Button>
        </form>
        {createError && <p className="mt-2 text-sm text-danger">{createError}</p>}
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}
      {channels === null && !error && <TableSkeleton rows={3} columns={4} />}
      {channels && channels.length === 0 && (
        <EmptyState title={t("noChannelsYet")} description={t("noChannelsDesc")} />
      )}

      <div className="flex flex-col gap-2">
        {channels?.map((channel) => (
          <Card key={channel.id} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ChannelTypeBadge channelType={channel.channel_type} />
              <div>
                <p className="font-medium text-text-primary">{channel.display_name}</p>
                {channel.identifier && <p className="text-xs text-text-secondary">{channel.identifier}</p>}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs font-medium ${channel.is_active ? "text-success" : "text-text-secondary"}`}>
                {channel.is_active ? t("active") : t("inactive")}
              </span>
              <Button variant="secondary" onClick={() => handleToggleActive(channel)}>
                {channel.is_active ? tCommon("deactivate") : tCommon("activate")}
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
