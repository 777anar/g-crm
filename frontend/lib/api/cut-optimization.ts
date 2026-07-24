import { apiDownload, apiRequest } from "../api-client";
import type {
  CutOptimizationBatchRun,
  CutOptimizationRun,
  PieceSpec,
  Paginated,
  RecommendOffcutsResponse,
} from "../types";

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

// ── Multi-slab / cross-job batch optimization (Phase 20) ─────────────────────

export type RunBatchCutOptimizationInput = {
  material_id: string;
  pieces: PieceSpec[];
  kerf_mm: string;
  slab_ids?: string[];
  thickness_mm?: string;
  finish?: string;
  warehouse_id?: string;
  max_slabs?: number;
  notes?: string;
};

export function runBatchCutOptimization(input: RunBatchCutOptimizationInput) {
  return apiRequest<CutOptimizationBatchRun>(`${BASE}/batch-runs`, { method: "POST", body: input });
}

export function listBatchCutOptimizationRuns(
  params: { materialId?: string; limit?: number; cursor?: string } = {}
) {
  return apiRequest<Paginated<CutOptimizationBatchRun>>(`${BASE}/batch-runs`, {
    searchParams: { material_id: params.materialId, limit: params.limit, cursor: params.cursor },
  });
}

export function getBatchCutOptimizationRun(id: string) {
  return apiRequest<CutOptimizationBatchRun>(`${BASE}/batch-runs/${id}`);
}

// ── CNC/machine-ready export (Phase 20) ───────────────────────────────────────

export function exportRunDxf(id: string) {
  return apiDownload(`${BASE}/runs/${id}/export.dxf`, { filename: `cut-optimization-${id}.dxf` });
}

export function exportBatchRunDxf(id: string) {
  return apiDownload(`${BASE}/batch-runs/${id}/export.dxf`, { filename: `cut-optimization-batch-${id}.dxf` });
}
