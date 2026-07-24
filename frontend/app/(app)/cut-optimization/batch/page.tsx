"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { exportBatchRunDxf, runBatchCutOptimization } from "@/lib/api/cut-optimization";
import { listMaterials, listSlabs } from "@/lib/api/catalog";
import type { CutOptimizationBatchRun, Material, PieceSpec, Slab } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextField } from "@/components/ui/field";
import { ApiRequestError } from "@/lib/api-client";
import { SlabLayoutSvg } from "@/components/cut-optimization/slab-layout-svg";
import { usePermission } from "@/lib/permissions";

type SlabMode = "auto" | "explicit";

function emptyPiece(label: string): PieceSpec {
  return { label, length_mm: "", width_mm: "", quantity: 1, allow_rotation: true };
}

export default function BatchCutOptimizationPage() {
  const t = useTranslations("cutOptimization");
  const tCommon = useTranslations("common");
  const canWrite = usePermission("cut_optimization:write");

  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialId, setMaterialId] = useState("");
  const [kerfMm, setKerfMm] = useState("3");
  const [maxSlabs, setMaxSlabs] = useState("20");

  const [slabMode, setSlabMode] = useState<SlabMode>("auto");
  const [availableSlabs, setAvailableSlabs] = useState<Slab[]>([]);
  const [selectedSlabIds, setSelectedSlabIds] = useState<string[]>([]);

  const [pieces, setPieces] = useState<PieceSpec[]>([emptyPiece("WO-1: Piece 1")]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CutOptimizationBatchRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    listMaterials({ limit: 100 }).then((r) => setMaterials(r.items)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!materialId) {
      setAvailableSlabs([]);
      setSelectedSlabIds([]);
      return;
    }
    listSlabs({ materialId, status: "available", limit: 100 }).then((r) => setAvailableSlabs(r.items)).catch(() => {});
  }, [materialId]);

  function updatePiece(index: number, patch: Partial<PieceSpec>) {
    setPieces((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }

  function addPiece() {
    setPieces((prev) => [...prev, emptyPiece(`WO-1: Piece ${prev.length + 1}`)]);
  }

  function removePiece(index: number) {
    setPieces((prev) => prev.filter((_, i) => i !== index));
  }

  function toggleSlab(id: string) {
    setSelectedSlabIds((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  }

  async function handleRun() {
    setError(null);
    setRunning(true);
    try {
      const run = await runBatchCutOptimization({
        material_id: materialId,
        pieces,
        kerf_mm: kerfMm,
        max_slabs: parseInt(maxSlabs, 10) || 20,
        ...(slabMode === "explicit" ? { slab_ids: selectedSlabIds } : {}),
      });
      setResult(run);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("runFailed"));
    } finally {
      setRunning(false);
    }
  }

  async function handleExport(id: string) {
    setExporting(true);
    try {
      await exportBatchRunDxf(id);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("exportFailed"));
    } finally {
      setExporting(false);
    }
  }

  const canRun =
    !!materialId &&
    pieces.length > 0 &&
    pieces.every((p) => p.label && p.length_mm && p.width_mm && p.quantity >= 1) &&
    (slabMode === "auto" || selectedSlabIds.length > 0);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("batchTitle")}</h1>
          <p className="text-sm text-text-secondary">{t("batchSubtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/cut-optimization">
            <Button variant="secondary">{t("title")}</Button>
          </Link>
          <Link href="/cut-optimization/batch/history">
            <Button variant="secondary">{t("historyLink")}</Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardHeader title={t("slabSection")} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SelectField label={t("material")} value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
            <option value="">{tCommon("select")}</option>
            {materials.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </SelectField>
          <TextField label={t("kerf")} value={kerfMm} onChange={(e) => setKerfMm(e.target.value)} />
          <TextField
            label={t("maxSlabs")} type="number" min={1} value={maxSlabs}
            onChange={(e) => setMaxSlabs(e.target.value)}
            hint={slabMode === "auto" ? t("maxSlabsHint") : undefined}
          />
        </div>

        <div className="mt-3 flex gap-2">
          <Button variant={slabMode === "auto" ? "primary" : "secondary"} onClick={() => setSlabMode("auto")}>
            {t("autoSelectSlabs")}
          </Button>
          <Button variant={slabMode === "explicit" ? "primary" : "secondary"} onClick={() => setSlabMode("explicit")}>
            {t("chooseSlabs")}
          </Button>
        </div>

        {slabMode === "explicit" && (
          <div className="mt-3 flex flex-col gap-2 rounded-md border border-border p-3">
            {!materialId && <p className="text-sm text-text-secondary">{t("selectMaterialFirst")}</p>}
            {materialId && availableSlabs.length === 0 && (
              <p className="text-sm text-text-secondary">{t("noAvailableSlabs")}</p>
            )}
            {availableSlabs.map((s) => (
              <label key={s.id} className="flex items-center gap-2 text-sm text-text-primary">
                <input type="checkbox" checked={selectedSlabIds.includes(s.id)} onChange={() => toggleSlab(s.id)} />
                {s.slab_number} ({s.length_mm}×{s.width_mm}mm{s.is_offcut ? ` · ${t("offcutTag")}` : ""})
              </label>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title={t("piecesSection")} action={<Button variant="secondary" onClick={addPiece}>{t("addPiece")}</Button>} />
        <p className="mb-3 text-xs text-text-secondary">{t("batchLabelHint")}</p>
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
            <Button onClick={handleRun} disabled={!canRun || running} loading={running}>
              {t("runBatchOptimization")}
            </Button>
          </div>
        )}
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {result && (
        <Card>
          <CardHeader
            title={t("resultSection")}
            action={
              <Button variant="secondary" onClick={() => handleExport(result.id)} loading={exporting}>
                {t("exportDxf")}
              </Button>
            }
          />
          <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
            <div>
              <p className="text-xs text-text-secondary">{t("slabsUsed")}</p>
              <p className="text-lg font-semibold text-text-primary">{result.slabs_used_count}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("utilization")}</p>
              <p className="text-lg font-semibold text-text-primary">{result.utilization_pct}%</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("wasteArea")}</p>
              <p className="text-lg font-semibold text-text-primary">{result.waste_area_m2} m²</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("placedArea")}</p>
              <p className="text-lg font-semibold text-text-primary">{result.placed_area_m2} m²</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{t("totalArea")}</p>
              <p className="text-lg font-semibold text-text-primary">{result.total_area_m2} m²</p>
            </div>
          </div>

          {result.unplaced.length > 0 && (
            <div className="mb-4 rounded-md border border-danger/30 bg-danger/5 p-3">
              <p className="text-sm font-medium text-danger">{t("unplacedWarning")}</p>
              <ul className="mt-1 list-disc pl-5 text-sm text-danger">
                {result.unplaced.map((u, i) => (
                  <li key={i}>{u.label} #{u.instance_index} — {u.reason}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-col gap-4">
            {result.slabs.map((slab) => (
              <div key={slab.slab_ref}>
                <p className="mb-2 text-sm font-medium text-text-primary">
                  {slab.slab_ref} ({slab.length_mm}×{slab.width_mm}mm)
                </p>
                <SlabLayoutSvg
                  slabLengthMm={parseFloat(slab.length_mm)}
                  slabWidthMm={parseFloat(slab.width_mm)}
                  placements={result.placements.filter((p) => p.slab_ref === slab.slab_ref)}
                />
              </div>
            ))}
          </div>

          <p className="mt-3 text-xs text-text-secondary">
            <Link href={`/cut-optimization/batch/history/${result.id}`} className="text-primary hover:underline">
              {t("viewInHistory")}
            </Link>
          </p>
        </Card>
      )}
    </div>
  );
}
