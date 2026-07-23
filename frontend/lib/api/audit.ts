import { apiDownload, apiRequest } from "../api-client";
import type { AuditLogEntry, Paginated, RetentionPolicy } from "../types";

export function listAuditLogs(
  params: {
    module?: string;
    entityType?: string;
    action?: string;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<AuditLogEntry>>("/api/v1/audit/logs", {
    searchParams: {
      module: params.module || undefined,
      entity_type: params.entityType || undefined,
      action: params.action || undefined,
      date_from: params.dateFrom || undefined,
      date_to: params.dateTo || undefined,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function exportAuditLogs(
  params: { module?: string; entityType?: string; action?: string; dateFrom?: string; dateTo?: string } = {}
) {
  return apiDownload("/api/v1/audit/logs/export", {
    searchParams: {
      module: params.module || undefined,
      entity_type: params.entityType || undefined,
      action: params.action || undefined,
      date_from: params.dateFrom || undefined,
      date_to: params.dateTo || undefined,
    },
    filename: "audit_log_export.csv",
  });
}

export function getRetentionPolicy() {
  return apiRequest<RetentionPolicy>("/api/v1/audit/retention-policy");
}

export function setRetentionPolicy(retentionDays: number | null) {
  return apiRequest<RetentionPolicy>("/api/v1/audit/retention-policy", {
    method: "PUT",
    body: { retention_days: retentionDays },
  });
}

export function purgeExpiredAuditLogs() {
  return apiRequest<{ deleted_count: number }>("/api/v1/audit/retention-policy/purge", { method: "POST" });
}
