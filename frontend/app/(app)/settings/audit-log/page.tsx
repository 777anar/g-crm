"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { exportAuditLogs, getRetentionPolicy, listAuditLogs, purgeExpiredAuditLogs, setRetentionPolicy } from "@/lib/api/audit";
import type { AuditLogEntry } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { usePermission } from "@/lib/permissions";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { useToast } from "@/components/ui/toast";

export default function AuditLogPage() {
  const t = useTranslations("auditLog");
  const tCommon = useTranslations("common");
  const canExport = usePermission("core:audit:export");
  const confirm = useConfirm();
  const toast = useToast();

  const [entries, setEntries] = useState<AuditLogEntry[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [module, setModule] = useState("");
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [retentionDays, setRetentionDays] = useState<string>("");
  const [retentionUpdatedAt, setRetentionUpdatedAt] = useState<string | null>(null);
  const [savingRetention, setSavingRetention] = useState(false);

  const reload = useCallback(
    async (options: { append?: boolean; cursor?: string } = {}) => {
      try {
        const res = await listAuditLogs({
          module: module || undefined,
          entityType: entityType || undefined,
          action: action || undefined,
          cursor: options.cursor,
        });
        setEntries((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
        setNextCursor(res.next_cursor);
      } catch (err) {
        setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
      }
    },
    [module, entityType, action, t]
  );

  useEffect(() => {
    if (!canExport) return;
    setEntries(null);
    reload();
  }, [canExport, reload]);

  useEffect(() => {
    if (!canExport) return;
    getRetentionPolicy()
      .then((policy) => {
        setRetentionDays(policy.retention_days != null ? String(policy.retention_days) : "");
        setRetentionUpdatedAt(policy.updated_at);
      })
      .catch(() => {});
  }, [canExport]);

  async function handleExport() {
    try {
      await exportAuditLogs({
        module: module || undefined,
        entityType: entityType || undefined,
        action: action || undefined,
      });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("exportFailed"));
    }
  }

  async function handleSaveRetention(e: React.FormEvent) {
    e.preventDefault();
    setSavingRetention(true);
    try {
      const days = retentionDays.trim() === "" ? null : Number(retentionDays);
      const policy = await setRetentionPolicy(days);
      setRetentionUpdatedAt(policy.updated_at);
      toast.success(t("retentionSaved"));
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : t("retentionSaveFailed"));
    } finally {
      setSavingRetention(false);
    }
  }

  async function handlePurge() {
    const ok = await confirm(t("purgeConfirm"), { confirmLabel: t("purgeNow") });
    if (!ok) return;
    try {
      const result = await purgeExpiredAuditLogs();
      toast.success(t("purgeSuccess", { count: result.deleted_count }));
      reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : t("purgeFailed"));
    }
  }

  if (!canExport) {
    return <EmptyState title={t("accessDeniedTitle")} description={t("accessDeniedDesc")} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("retentionTitle")} />
        <form className="flex flex-wrap items-end gap-3" onSubmit={handleSaveRetention}>
          <TextField
            label={t("retentionDays")}
            type="number"
            min={1}
            value={retentionDays}
            onChange={(e) => setRetentionDays(e.target.value)}
            hint={t("retentionHint")}
          />
          <Button type="submit" disabled={savingRetention}>
            {savingRetention ? t("saving") : tCommon("save")}
          </Button>
          <Button type="button" variant="destructive" onClick={handlePurge}>
            {t("purgeNow")}
          </Button>
          {retentionUpdatedAt && (
            <span className="text-xs text-text-secondary">
              {t("retentionUpdatedAt", { date: new Date(retentionUpdatedAt).toLocaleString() })}
            </span>
          )}
        </form>
      </Card>

      <Card>
        <CardHeader title={t("logsTitle")} />
        <div className="flex flex-wrap items-end gap-3">
          <TextField label={t("filterModule")} value={module} onChange={(e) => setModule(e.target.value)} />
          <TextField label={t("filterEntityType")} value={entityType} onChange={(e) => setEntityType(e.target.value)} />
          <TextField label={t("filterAction")} value={action} onChange={(e) => setAction(e.target.value)} />
          <Button variant="secondary" onClick={() => reload()}>
            {tCommon("filters")}
          </Button>
          <Button variant="secondary" onClick={handleExport}>
            {t("exportCsv")}
          </Button>
        </div>

        {error && <p className="mt-3 text-sm text-danger">{error}</p>}

        {entries === null && !error && <TableSkeleton rows={6} columns={6} />}

        {entries && entries.length === 0 && (
          <EmptyState title={t("noEntriesYet")} description={t("noEntriesDesc")} />
        )}

        {entries && entries.length > 0 && (
          <>
            <div className={tableScrollShellClass}>
              <table className="w-full text-left text-sm">
                <thead className={stickyTheadClass}>
                  <tr>
                    <th className="px-4 py-2 font-medium">{t("colTime")}</th>
                    <th className="px-4 py-2 font-medium">{t("colModule")}</th>
                    <th className="px-4 py-2 font-medium">{t("colAction")}</th>
                    <th className="px-4 py-2 font-medium">{t("colEntityType")}</th>
                    <th className="px-4 py-2 font-medium">{t("colEntityId")}</th>
                    <th className="px-4 py-2 font-medium">{t("colActor")}</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr key={entry.id} className="border-b border-border last:border-0 hover:bg-bg">
                      <td className="px-4 py-2 text-text-secondary">{new Date(entry.created_at).toLocaleString()}</td>
                      <td className="px-4 py-2 text-text-primary">{entry.module}</td>
                      <td className="px-4 py-2 text-text-secondary">{entry.action}</td>
                      <td className="px-4 py-2 text-text-secondary">{entry.entity_type}</td>
                      <td className="px-4 py-2 font-mono text-xs text-text-secondary">{entry.entity_id}</td>
                      <td className="px-4 py-2 font-mono text-xs text-text-secondary">{entry.actor_user_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {nextCursor && (
              <div className="mt-3 flex justify-center">
                <Button variant="secondary" onClick={() => reload({ append: true, cursor: nextCursor })}>
                  {tCommon("loadMore")}
                </Button>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
