"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { recommendOffcuts } from "@/lib/api/cut-optimization";
import { listMaterials } from "@/lib/api/catalog";
import type { Material, PieceSpec, RecommendOffcutsResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextField } from "@/components/ui/field";
import { ApiRequestError } from "@/lib/api-client";
import { SlabLayoutSvg } from "@/components/cut-optimization/slab-layout-svg";
import { usePermission } from "@/lib/permissions";

function emptyPiece(label: string): PieceSpec {
  return { label, length_mm: "", width_mm: "", quantity: 1, allow_rotation: true };
}

export default function OffcutRecommendationsPage() {
  const t = useTranslations("cutOptimization");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const canWrite = usePermission("cut_optimization:write");

  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialId, setMaterialId] = useState("");
  const [thicknessMm, setThicknessMm] = useState("");
  const [finish, setFinish] = useState("");
  const [kerfMm, setKerfMm] = useState("3");
  const [pieces, setPieces] = useState<PieceSpec[]>([emptyPiece("Piece 1")]);

  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<RecommendOffcutsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMaterials({ limit: 100 }).then((r) => setMaterials(r.items)).catch(() => {});
  }, []);

  function updatePiece(index: number, patch: Partial<PieceSpec>) {
    setPieces((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }
  function addPiece() {
    setPieces((prev) => [...prev, emptyPiece(`Piece ${prev.length + 1}`)]);
  }
  function removePiece(index: number) {
    setPieces((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSearch() {
    setError(null);
    setSearching(true);
    setResult(null);
    try {
      const res = await recommendOffcuts({
        material_id: materialId,
        pieces,
        kerf_mm: kerfMm,
        thickness_mm: thicknessMm || undefined,
        finish: finish || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("runFailed"));
    } finally {
      setSearching(false);
    }
  }

  const canSearch = !!materialId && pieces.every((p) => p.label && p.length_mm && p.width_mm);

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("cutOptimization"), href: "/cut-optimization" }, { label: t("findOffcutLink") }]} />

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("recommendationsTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("recommendationsSubtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("requirementSection")} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <SelectField label={t("material")} value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
            <option value="">{tCommon("select")}</option>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </SelectField>
          <TextField label={t("thickness")} value={thicknessMm} onChange={(e) => setThicknessMm(e.target.value)} placeholder="20" />
          <TextField label={t("finish")} value={finish} onChange={(e) => setFinish(e.target.value)} placeholder="Polished" />
          <TextField label={t("kerf")} value={kerfMm} onChange={(e) => setKerfMm(e.target.value)} />
        </div>
      </Card>

      <Card>
        <CardHeader title={t("piecesSection")} action={<Button variant="secondary" onClick={addPiece}>{t("addPiece")}</Button>} />
        <div className="flex flex-col gap-3">
          {pieces.map((piece, index) => (
            <div key={index} className="grid grid-cols-1 gap-3 rounded-md border border-border p-3 sm:grid-cols-5">
              <TextField label={t("pieceLabel")} value={piece.label} onChange={(e) => updatePiece(index, { label: e.target.value })} />
              <TextField label={t("pieceLength")} value={piece.length_mm} onChange={(e) => updatePiece(index, { length_mm: e.target.value })} />
              <TextField label={t("pieceWidth")} value={piece.width_mm} onChange={(e) => updatePiece(index, { width_mm: e.target.value })} />
              <TextField
                label={t("pieceQuantity")} type="number" min={1} value={piece.quantity}
                onChange={(e) => updatePiece(index, { quantity: Math.max(1, parseInt(e.target.value, 10) || 1) })}
              />
              <div className="flex items-end justify-between gap-2">
                <label className="flex items-center gap-2 text-sm text-text-primary">
                  <input type="checkbox" checked={piece.allow_rotation} onChange={(e) => updatePiece(index, { allow_rotation: e.target.checked })} />
                  {t("allowRotation")}
                </label>
                {pieces.length > 1 && (
                  <Button variant="destructive" onClick={() => removePiece(index)}>{tCommon("remove")}</Button>
                )}
              </div>
            </div>
          ))}
        </div>
        {canWrite && (
          <div className="mt-4 flex justify-end">
            <Button onClick={handleSearch} disabled={!canSearch || searching} loading={searching}>
              {t("findBestOffcut")}
            </Button>
          </div>
        )}
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {result && (
        <Card className={result.recommend_new_slab ? "border-warning/30 bg-warning/5" : "border-success/30 bg-success/5"}>
          <p className={`text-sm font-medium ${result.recommend_new_slab ? "text-warning" : "text-success"}`}>
            {result.recommend_new_slab ? t("recommendNewSlab") : t("offcutsAvailable")}
          </p>
          <p className="mt-1 text-sm text-text-secondary">{result.reason}</p>
        </Card>
      )}

      {result && result.candidates.length > 0 && (
        <div className="flex flex-col gap-4">
          {result.candidates.map((candidate, i) => (
            <Card key={candidate.slab_id} className={i === 0 && candidate.fits ? "border-primary/50" : ""}>
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <p className="font-mono font-medium text-text-primary">{candidate.slab_number}</p>
                  {i === 0 && candidate.fits && <Badge tone="success">{t("bestFit")}</Badge>}
                  <Badge tone={candidate.fits ? "success" : "danger"}>
                    {candidate.fits ? t("fits") : t("doesNotFit")}
                  </Badge>
                </div>
                <p className="text-sm text-text-secondary">
                  {t("utilization")}: {candidate.utilization_pct}% · {t("wasteArea")}: {candidate.waste_area_m2} m²
                </p>
              </div>
              <p className="mb-3 text-sm text-text-secondary">{candidate.explanation}</p>
              {candidate.fits && (
                <SlabLayoutSvg
                  slabLengthMm={parseFloat(candidate.slab_length_mm)}
                  slabWidthMm={parseFloat(candidate.slab_width_mm)}
                  placements={candidate.placements}
                />
              )}
            </Card>
          ))}
        </div>
      )}

      {result?.persisted_run_id && (
        <p className="text-xs text-text-secondary">
          <Link href={`/cut-optimization/history/${result.persisted_run_id}`} className="text-primary hover:underline">
            {t("viewInHistory")}
          </Link>
        </p>
      )}
    </div>
  );
}
