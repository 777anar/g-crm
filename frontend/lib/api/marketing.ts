import { apiRequest } from "../api-client";
import type { Campaign, CampaignPerformance, Paginated } from "../types";

const BASE = "/api/v1/marketing";

export function listCampaigns(
  params: {
    status?: string;
    channel?: string;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Campaign>>(`${BASE}/campaigns`, {
    searchParams: {
      status: params.status,
      channel: params.channel,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function createCampaign(input: {
  name: string;
  channel: string;
  start_date?: string;
  end_date?: string;
  budget?: string;
  currency?: string;
  notes?: string;
}) {
  return apiRequest<Campaign>(`${BASE}/campaigns`, { method: "POST", body: input });
}

export function getCampaign(id: string) {
  return apiRequest<Campaign>(`${BASE}/campaigns/${id}`);
}

export function updateCampaign(
  id: string,
  input: Partial<{
    name: string;
    channel: string;
    start_date: string;
    end_date: string;
    budget: string;
    notes: string;
  }>
) {
  return apiRequest<Campaign>(`${BASE}/campaigns/${id}`, { method: "PATCH", body: input });
}

export function updateCampaignStatus(id: string, status: string) {
  return apiRequest<Campaign>(`${BASE}/campaigns/${id}/status`, { method: "POST", body: { status } });
}

export function getCampaignPerformance(id: string) {
  return apiRequest<CampaignPerformance>(`${BASE}/campaigns/${id}/performance`);
}
