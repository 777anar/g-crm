import { apiRequest } from "../api-client";
import type { CutOptimizationRun, PieceSpec, Paginated, RecommendOffcutsResponse } from "../types";

const BASE = "/api/v1/cut_optimization";

export type RunCutOptimizationInput = {
  pieces: PieceSpec[];
  kerf_mm: string;
  slab_id?: string;
  slab_length_mm?: string;
  slab_width_mm?: string;
  material_id?: string;
  notes?: string;
};

export function runCutOptimization(input: RunCutOptimizationInput) {
  return apiRequest<CutOptimizationRun>(`${BASE}/runs`, { method: "POST", body: input });
}

export function listCutOptimizationRuns(
  params: { materialId?: string; slabId?: string; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<CutOptimizationRun>>(`${BASE}/runs`, {
    searchParams: {
      material_id: params.materialId,
      slab_id: params.slabId,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function getCutOptimizationRun(id: string) {
  return apiRequest<CutOptimizationRun>(`${BASE}/runs/${id}`);
}

export type RecommendOffcutsInput = {
  material_id: string;
  pieces: PieceSpec[];
  kerf_mm: string;
  thickness_mm?: string;
  finish?: string;
  warehouse_id?: string;
  persist_top_candidate?: boolean;
};

export function recommendOffcuts(input: RecommendOffcutsInput) {
  return apiRequest<RecommendOffcutsResponse>(`${BASE}/recommendations`, { method: "POST", body: input });
}
