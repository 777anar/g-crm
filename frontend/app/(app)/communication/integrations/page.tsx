"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  configureChannelCredential,
  getChannelCredential,
  listChannels,
  listIntegrationLogs,
  listMessageQueue,
  processMessageQueue,
  removeChannelCredential,
  syncImapMailbox,
  testChannelConnection,
} from "@/lib/api/communication";
import {
  PROVIDERS_FOR_CHANNEL_TYPE,
  type Channel,
  type ChannelCredential,
  type IntegrationLogEntry,
  type MessageQueueEntry,
  type ProviderName,
} from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TextField, SelectField } from "@/components/ui/field";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { tableScrollShellClass, stickyTheadClass } from "@/components/ui/data-table";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";

type FieldDef = { key: string; label: string; secret?: boolean; type?: string };

const PROVIDER_FIELDS: Record<ProviderName, FieldDef[]> = {
  meta_whatsapp: [
    { key: "phone_number_id", label: "Phone Number ID" },
    { key: "access_token", label: "Access Token", secret: true },
    { key: "app_secret", label: "App Secret", secret: true },
    { key: "verify_token", label: "Verify Token" },
  ],
  meta_instagram: [
    { key: "ig_user_id", label: "Instagram User ID" },
    { key: "access_token", label: "Access Token", secret: true },
    { key: "app_secret", label: "App Secret", secret: true },
    { key: "verify_token", label: "Verify Token" },
  ],
  meta_messenger: [
    { key: "page_id", label: "Page ID" },
    { key: "page_access_token", label: "Page Access Token", secret: true },
    { key: "app_secret", label: "App Secret", secret: true },
    { key: "verify_token", label: "Verify Token" },
  ],
  smtp: [
    { key: "smtp_host", label: "SMTP Host" },
    { key: "smtp_port", label: "SMTP Port" },
    { key: "smtp_username", label: "SMTP Username" },
    { key: "smtp_password", label: "SMTP Password", secret: true },
    { key: "smtp_encryption", label: "Encryption (starttls/ssl/none)" },
    { key: "from_address", label: "From Address" },
    { key: "imap_host", label: "IMAP Host" },
    { key: "imap_port", label: "IMAP Port" },
    { key: "imap_username", label: "IMAP Username" },
    { key: "imap_password", label: "IMAP Password", secret: true },
    { key: "imap_folder", label: "IMAP Folder" },
  ],
  twilio_sms: [
    { key: "account_sid", label: "Account SID" },
    { key: "auth_token", label: "Auth Token", secret: true },
    { key: "from_number", label: "From Number" },
  ],
  webhook: [
    { key: "outbound_url", label: "Outbound URL" },
    { key: "secret", label: "Shared Secret", secret: true },
  ],
};

const HEALTH_TONE: Record<string, "neutral" | "success" | "danger"> = {
  unknown: "neutral",
  ok: "success",
  error: "danger",
};

export default function IntegrationsPage() {
  const t = useTranslations("integrations");
  const tCommon = useTranslations("common");
  const toast = useToast();

  const [channels, setChannels] = useState<Channel[] | null>(null);
  const [credentials, setCredentials] = useState<Record<string, ChannelCredential | null>>({});
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [selectedProvider, setSelectedProvider] = useState<ProviderName | "">("");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [queue, setQueue] = useState<MessageQueueEntry[] | null>(null);
  const [logs, setLogs] = useState<IntegrationLogEntry[] | null>(null);
  const [logsDirection, setLogsDirection] = useState("");
  const [processingQueue, setProcessingQueue] = useState(false);

  const loadChannels = useCallback(async () => {
    try {
      const res = await listChannels();
      setChannels(res.items);
      const entries = await Promise.all(
        res.items.map(async (channel) => {
          try {
            const credential = await getChannelCredential(channel.id);
            return [channel.id, credential] as const;
          } catch {
            return [channel.id, null] as const;
          }
        })
      );
      setCredentials(Object.fromEntries(entries));
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }, [t]);

  const loadQueue = useCallback(() => {
    listMessageQueue({ limit: 100 }).then((r) => setQueue(r.items)).catch(() => {});
  }, []);

  const loadLogs = useCallback(() => {
    listIntegrationLogs({ direction: logsDirection || undefined, limit: 100 })
      .then((r) => setLogs(r.items))
      .catch(() => {});
  }, [logsDirection]);

  useEffect(() => { loadChannels(); }, [loadChannels]);
  useEffect(() => { loadQueue(); }, [loadQueue]);
  useEffect(() => { loadLogs(); }, [loadLogs]);

  function startConfiguring(channel: Channel) {
    setExpandedId(channel.id);
    const providers = PROVIDERS_FOR_CHANNEL_TYPE[channel.channel_type] ?? [];
    setSelectedProvider(providers[0] ?? "");
    setForm({});
  }

  async function handleSave(channelId: string) {
    if (!selectedProvider) return;
    setBusyId(channelId);
    setError(null);
    try {
      const config: Record<string, string> = {};
      for (const field of PROVIDER_FIELDS[selectedProvider]) {
        if (form[field.key]) config[field.key] = form[field.key];
      }
      await configureChannelCredential(channelId, { provider: selectedProvider, config });
      toast.success(t("credentialSaved"));
      setExpandedId(null);
      await loadChannels();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("saveFailed"));
    } finally {
      setBusyId(null);
    }
  }

  async function handleRemove(channelId: string) {
    setBusyId(channelId);
    try {
      await removeChannelCredential(channelId);
      toast.success(t("credentialRemoved"));
      await loadChannels();
    } finally {
      setBusyId(null);
    }
  }

  async function handleTestConnection(channelId: string) {
    setBusyId(channelId);
    try {
      const result = await testChannelConnection(channelId);
      if (result.ok) toast.success(result.detail || t("connectionOk"));
      else toast.error(result.detail || t("connectionFailed"));
      await loadChannels();
      loadLogs();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : t("connectionFailed"));
    } finally {
      setBusyId(null);
    }
  }

  async function handleImapSync(channelId: string) {
    setBusyId(channelId);
    try {
      const result = await syncImapMailbox(channelId);
      toast.success(t("syncComplete", { count: result.synced_count }));
      loadLogs();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : t("syncFailed"));
    } finally {
      setBusyId(null);
    }
  }

  async function handleProcessQueue() {
    setProcessingQueue(true);
    try {
      const result = await processMessageQueue();
      toast.success(t("queueProcessed", { sent: result.sent, failed: result.failed }));
      loadQueue();
      loadLogs();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : t("queueProcessFailed"));
    } finally {
      setProcessingQueue(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <Card>
        <CardHeader title={t("channelsSection")} />
        {channels === null && <TableSkeleton rows={3} columns={4} />}
        {channels && channels.length === 0 && <EmptyState title={t("noChannelsYet")} />}
        <div className="flex flex-col gap-3">
          {channels?.map((channel) => {
            const credential = credentials[channel.id];
            const providers = PROVIDERS_FOR_CHANNEL_TYPE[channel.channel_type] ?? [];
            const isImapCapable = channel.channel_type === "email";
            return (
              <div key={channel.id} className="rounded-md border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium text-text-primary">
                      {channel.display_name} <span className="text-xs text-text-secondary">({channel.channel_type})</span>
                    </p>
                    {credential && (
                      <div className="mt-1 flex items-center gap-2 text-xs text-text-secondary">
                        <Badge tone={HEALTH_TONE[credential.health_status] ?? "neutral"}>
                          {t(`health_${credential.health_status}` as any)}
                        </Badge>
                        <span>{credential.provider}</span>
                        {credential.last_error && <span className="text-danger">{credential.last_error}</span>}
                      </div>
                    )}
                    {!credential && <p className="mt-1 text-xs text-text-secondary">{t("noProviderConfigured")}</p>}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {providers.length > 0 && (
                      <Button variant="secondary" onClick={() => startConfiguring(channel)}>
                        {credential ? t("reconfigure") : t("configure")}
                      </Button>
                    )}
                    {credential && (
                      <>
                        <Button
                          variant="secondary"
                          loading={busyId === channel.id}
                          onClick={() => handleTestConnection(channel.id)}
                        >
                          {t("testConnection")}
                        </Button>
                        {isImapCapable && (
                          <Button
                            variant="secondary"
                            loading={busyId === channel.id}
                            onClick={() => handleImapSync(channel.id)}
                          >
                            {t("syncNow")}
                          </Button>
                        )}
                        <Button variant="destructive" loading={busyId === channel.id} onClick={() => handleRemove(channel.id)}>
                          {t("removeCredential")}
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {expandedId === channel.id && (
                  <div className="mt-3 flex flex-col gap-3 border-t border-border pt-3">
                    {providers.length > 1 && (
                      <SelectField
                        label={t("provider")}
                        value={selectedProvider}
                        onChange={(e) => setSelectedProvider(e.target.value as ProviderName)}
                      >
                        {providers.map((p) => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </SelectField>
                    )}
                    {selectedProvider && (
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {PROVIDER_FIELDS[selectedProvider].map((field) => (
                          <TextField
                            key={field.key}
                            label={field.label}
                            type={field.secret ? "password" : "text"}
                            value={form[field.key] ?? ""}
                            onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
                          />
                        ))}
                      </div>
                    )}
                    <div className="flex gap-2">
                      <Button loading={busyId === channel.id} onClick={() => handleSave(channel.id)}>
                        {tCommon("save")}
                      </Button>
                      <Button variant="secondary" onClick={() => setExpandedId(null)}>
                        {tCommon("cancel")}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <CardHeader
          title={t("queueSection")}
          action={
            <Button variant="secondary" loading={processingQueue} onClick={handleProcessQueue}>
              {t("processQueue")}
            </Button>
          }
        />
        {queue === null && <TableSkeleton rows={3} columns={4} />}
        {queue && queue.length === 0 && <EmptyState title={t("noQueueEntries")} />}
        {queue && queue.length > 0 && (
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-3 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableAttempts")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableNextAttempt")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableLastError")}</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((entry) => (
                  <tr key={entry.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2">
                      <Badge tone={entry.status === "sent" ? "success" : entry.status === "failed" ? "danger" : "warning"}>
                        {entry.status}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-text-secondary">{entry.attempts}/{entry.max_attempts}</td>
                    <td className="px-3 py-2 text-text-secondary">
                      {entry.next_attempt_at ? formatDateTime(entry.next_attempt_at) : tCommon("dash")}
                    </td>
                    <td className="px-3 py-2 text-danger">{entry.last_error ?? tCommon("dash")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader
          title={t("logsSection")}
          action={
            <select
              value={logsDirection}
              onChange={(e) => setLogsDirection(e.target.value)}
              className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
            >
              <option value="">{t("allDirections")}</option>
              <option value="outbound">{t("outbound")}</option>
              <option value="inbound">{t("inboundWebhookMonitor")}</option>
            </select>
          }
        />
        {logs === null && <TableSkeleton rows={4} columns={5} />}
        {logs && logs.length === 0 && <EmptyState title={t("noLogsYet")} />}
        {logs && logs.length > 0 && (
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-3 py-2 font-medium">{t("tableDirection")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableProvider")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableAction")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableResult")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableDuration")}</th>
                  <th className="px-3 py-2 font-medium">{t("tableWhen")}</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((entry) => (
                  <tr key={entry.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2 text-text-secondary">{entry.direction}</td>
                    <td className="px-3 py-2 text-text-secondary">{entry.provider}</td>
                    <td className="px-3 py-2 text-text-secondary">{entry.action}</td>
                    <td className="px-3 py-2">
                      <Badge tone={entry.success ? "success" : "danger"}>
                        {entry.success ? t("success") : t("failure")}
                      </Badge>
                      {entry.error_message && <p className="mt-0.5 text-xs text-danger">{entry.error_message}</p>}
                    </td>
                    <td className="px-3 py-2 text-text-secondary">
                      {entry.duration_ms !== null ? `${entry.duration_ms} ms` : tCommon("dash")}
                    </td>
                    <td className="px-3 py-2 text-text-secondary">{formatDateTime(entry.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
