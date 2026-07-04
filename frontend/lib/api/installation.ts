import { apiRequest } from "../api-client";
import type {
  Crew,
  CrewMember,
  InstallationJob,
  InstallationNotification,
  InstallationPhoto,
  Paginated,
} from "../types";

const BASE = "/api/v1/installation";

// ── Crews ─────────────────────────────────────────────────────────────────────

export function listCrews(params: { status?: string } = {}) {
  return apiRequest<{ items: Crew[] }>(`${BASE}/crews`, { searchParams: { status: params.status } });
}

export function createCrew(input: { name: string; notes?: string }) {
  return apiRequest<Crew>(`${BASE}/crews`, { method: "POST", body: input });
}

export function getCrew(id: string) {
  return apiRequest<Crew>(`${BASE}/crews/${id}`);
}

export function updateCrew(id: string, input: { name?: string; status?: string; notes?: string }) {
  return apiRequest<Crew>(`${BASE}/crews/${id}`, { method: "PATCH", body: input });
}

export function listCrewMembers(crewId: string) {
  return apiRequest<{ items: CrewMember[] }>(`${BASE}/crews/${crewId}/members`);
}

export function addCrewMember(crewId: string, input: { user_id: string; is_lead?: boolean }) {
  return apiRequest<CrewMember>(`${BASE}/crews/${crewId}/members`, { method: "POST", body: input });
}

export function removeCrewMember(crewId: string, memberId: string) {
  return apiRequest<void>(`${BASE}/crews/${crewId}/members/${memberId}`, { method: "DELETE" });
}

// ── Installation jobs ─────────────────────────────────────────────────────────

export function listInstallationJobs(
  params: {
    status?: string;
    crewId?: string;
    dateFrom?: string;
    dateTo?: string;
    search?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<InstallationJob>>(`${BASE}/jobs`, {
    searchParams: {
      status: params.status,
      crew_id: params.crewId,
      date_from: params.dateFrom,
      date_to: params.dateTo,
      search: params.search || undefined,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createInstallationJob(orderId: string) {
  return apiRequest<InstallationJob>(`${BASE}/jobs`, { method: "POST", body: { order_id: orderId } });
}

export function getInstallationJob(id: string) {
  return apiRequest<InstallationJob>(`${BASE}/jobs/${id}`);
}

export function getInstallationJobForOrder(orderId: string) {
  return apiRequest<InstallationJob>(`${BASE}/jobs/by-order/${orderId}`);
}

export function updateInstallationJob(
  id: string,
  input: {
    crew_id?: string | null;
    scheduled_date?: string | null;
    scheduled_time_slot?: string | null;
    route_sequence?: number | null;
    notes?: string | null;
  }
) {
  return apiRequest<InstallationJob>(`${BASE}/jobs/${id}`, { method: "PATCH", body: input });
}

export function updateInstallationJobStatus(
  id: string,
  status: string,
  extra: { cancelledReason?: string; completionNotes?: string } = {}
) {
  return apiRequest<InstallationJob>(`${BASE}/jobs/${id}/status`, {
    method: "POST",
    body: { status, cancelled_reason: extra.cancelledReason, completion_notes: extra.completionNotes },
  });
}

export function listInstallationPhotos(jobId: string) {
  return apiRequest<{ items: InstallationPhoto[] }>(`${BASE}/jobs/${jobId}/photos`);
}

export function addInstallationPhoto(
  jobId: string,
  input: { document_id: string; photo_type: string; caption?: string; sort_order?: number }
) {
  return apiRequest<InstallationPhoto>(`${BASE}/jobs/${jobId}/photos`, { method: "POST", body: input });
}

export function uploadInstallationAsset(jobId: string, file: File) {
  const formData = new FormData();
  formData.append("module", "installation");
  formData.append("related_entity_type", "installation_job");
  formData.append("related_entity_id", jobId);
  formData.append("file", file);
  return apiRequest<{ id: string; storage_path: string; mime_type: string }>("/api/v1/core/documents", {
    method: "POST",
    formData,
  });
}

export function getDocumentUrl(documentId: string) {
  return apiRequest<{ url: string }>(`/api/v1/core/documents/${documentId}`);
}

// ── Notifications ─────────────────────────────────────────────────────────────

export function listNotifications(params: { unreadOnly?: boolean } = {}) {
  return apiRequest<{ items: InstallationNotification[] }>(`${BASE}/notifications`, {
    searchParams: { unread_only: params.unreadOnly },
  });
}

export function markNotificationRead(id: string) {
  return apiRequest<InstallationNotification>(`${BASE}/notifications/${id}/read`, { method: "POST" });
}
