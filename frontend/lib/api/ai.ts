import { apiRequest } from "../api-client";
import type { AIDashboard, AIRecommendation, AIUsage, Paginated } from "../types";

const BASE = "/api/v1/ai";

// ── Analysis triggers ────────────────────────────────────────────────────────

export function analyzeLead(leadId: string, provider?: string) {
  return apiRequest<{ items: AIRecommendation[] }>(`${BASE}/leads/${leadId}/analyze`, {
    method: "POST",
    body: { provider },
  });
}

export function analyzeConversation(conversationId: string, provider?: string) {
  return apiRequest<{ items: AIRecommendation[] }>(`${BASE}/conversations/${conversationId}/analyze`, {
    method: "POST",
    body: { provider },
  });
}

export function analyzeQuote(quoteId: string, provider?: string) {
  return apiRequest<{ items: AIRecommendation[] }>(`${BASE}/quotes/${quoteId}/analyze`, {
    method: "POST",
    body: { provider },
  });
}

export function suggestTasks(provider?: string) {
  return apiRequest<{ items: AIRecommendation[] }>(`${BASE}/tasks/suggest`, {
    method: "POST",
    body: { provider },
  });
}

// ── Recommendations ───────────────────────────────────────────────────────────

export function listRecommendations(
  params: {
    analysisKind?: string;
    recommendationType?: string;
    relatedEntityType?: string;
    relatedEntityId?: string;
    status?: string;
    provider?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<AIRecommendation>>(`${BASE}/recommendations`, {
    searchParams: {
      analysis_kind: params.analysisKind,
      recommendation_type: params.recommendationType,
      related_entity_type: params.relatedEntityType,
      related_entity_id: params.relatedEntityId,
      status: params.status,
      provider: params.provider,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getRecommendation(id: string) {
  return apiRequest<AIRecommendation>(`${BASE}/recommendations/${id}`);
}

export function reviewRecommendation(
  id: string,
  decision: "accept" | "reject" | "edit",
  editedResponse?: Record<string, unknown>
) {
  return apiRequest<AIRecommendation>(`${BASE}/recommendations/${id}/review`, {
    method: "POST",
    body: { decision, edited_response: editedResponse },
  });
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export function getAIDashboard() {
  return apiRequest<AIDashboard>(`${BASE}/dashboard`);
}

// ── Usage & cost control (Phase 21) ──────────────────────────────────────────

export function getAIUsage(params: { limit?: number; offset?: number } = {}) {
  return apiRequest<AIUsage>(`${BASE}/usage`, {
    searchParams: { limit: params.limit, offset: params.offset },
  });
}
