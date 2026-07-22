"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { runCutOptimization } from "@/lib/api/cut-optimization";
import { listMaterials, listSlabs } from "@/lib/api/catalog";
import type { CutOptimizationRun, Material, PieceSpec, Slab } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextField } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { SlabLayoutSvg } from "@/components/cut-optimization/slab-layout-svg";

type SlabMode = "custom" | "existing";

function emptyPiece(label: string): PieceSpec {
  return { label, length_mm: "", width_mm: "", quantity: 1, allow_rotation: true };
}

export default function CutOptimizationPage() {
  const t = useTranslations("cutOptimization");
  const tCommon = useTranslations("common");
  const toast = useToast();

  const [slabMode, setSlabMode] = useState<SlabMode>("custom");
  const [slabLengthMm, setSlabLengthMm] = useState("3200");
  const [slabWidthMm, setSlabWidthMm] = useState("1600");
  const [kerfMm, setKerfMm] = useState("3");

  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialId, setMaterialId] = useState("");
  const [slabs, setSlabs] = useState<Slab[]>([]);
  const [slabId, setSlabId] = useState("");

  const [pieces, setPieces] = useState<PieceSpec[]>([emptyPiece("Piece 1")]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CutOptimizationRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMaterials({ limit: 100 }).then((r) => setMaterials(r.items)).catch(() => {});
  }, []);

  useEffect(() => {
    if (slabMode !== "existing" || !materialId) {
      setSlabs([]);
      return;
    }
    listSlabs({ materialId, status: "available", limit: 100 }).then((r) => setSlabs(r.items)).catch(() => {});
  }, [slabMode, materialId]);

  const selectedSlab = slabs.find((s) => s.id === slabId) ?? null;

  function updatePiece(index: number, patch: Partial<PieceSpec>) {
    setPieces((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  }

  function addPiece() {
    setPieces((prev) => [...prev, emptyPiece(`Piece ${prev.length + 1}`)]);
  }

  function removePiece(index: number) {
    setPieces((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleRun() {
    setError(null);
    setRunning(true);
    try {
      const run = await runCutOptimization({
        pieces,
        kerf_mm: kerfMm,
        ...(slabMode === "existing" && selectedSlab
          ? { slab_id: selectedSlab.id }
          : { slab_length_mm: slabLengthMm, slab_width_mm: slabWidthMm }),
        material_id: slabMode === "existing" ? materialId || undefined : undefined,
      });
      setResult(run);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("runFailed"));
    } finally {
      setRunning(false);
    }
  }

  const effectiveLength = slabMode === "existing" && selectedSlab ? selectedSlab.length_mm ?? "0" : slabLengthMm;
  const effectiveWidth = slabMode === "existing" && selectedSlab ? selectedSlab.width_mm ?? "0" : slabWidthMm;
  const canRun =
    pieces.length > 0 &&
    pieces.every((p) => p.label && p.length_mm && p.width_mm && p.quantity >= 1) &&
    (slabMode === "custom" ? !!slabLengthMm && !!slabWidthMm : !!selectedSlab);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
          <p className="text-sm text-text-secondary">{t("subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/cut-optimization/recommendations">
            <Button variant="secondary">{t("findOffcutLink")}</Button>
          </Link>
          <Link href="/cut-optimization/history">
            <Button variant="secondary">{t("historyLink")}</Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardHeader title={t("slabSection")} />
        <div className="mb-3 flex gap-2">
          <Button variant={slabMode === "custom" ? "primary" : "secondary"} onClick={() => setSlabMode("custom")}>
            {t("customSlab")}
          </Button>
          <Button variant={slabMode === "existing" ? "primary" : "secondary"} onClick={() => setSlabMode("existing")}>
            {t("existingSlab")}
          </Button>
        </div>

        {slabMode === "custom" ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <TextField label={t("slabLength")} value={slabLengthMm} onChange={(e) => setSlabLengthMm(e.target.value)} />
            <TextField label={t("slabWidth")} value={slabWidthMm} onChange={(e) => setSlabWidthMm(e.target.value)} />
            <TextField label={t("kerf")} value={kerfMm} onChange={(e) => setKerfMm(e.target.value)} />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <SelectField label={t("material")} value={materialId} onChange={(e) => { setMaterialId(e.target.value); setSlabId(""); }}>
              <option value="">{tCommon("select")}</option>
              {materials.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </SelectField>
            <SelectField label={t("slab")} value={slabId} onChange={(e) => setSlabId(e.target.value)} disabled={!materialId}>
              <option value="">{tCommon("select")}</option>
              {slabs.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.slab_number} ({s.length_mm}×{s.width_mm}mm{s.is_offcut ? ` · ${t("offcutTag")}` : ""})
                </option>
              ))}
            </SelectField>
            <TextField label={t("kerf")} value={kerfMm} onChange={(e) => setKerfMm(e.target.value)} />
          </div>
        )}
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
        <div className="mt-4 flex justify-end">
          <Button onClick={handleRun} disabled={!canRun || running} loading={running}>
            {t("runOptimization")}
          </Button>
        </div>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {result && (
        <Card>
          <CardHeader title={t("resultSection")} />
          <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
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

          <SlabLayoutSvg
            slabLengthMm={parseFloat(result.slab_length_mm)}
            slabWidthMm={parseFloat(result.slab_width_mm)}
            placements={result.placements}
          />

          {result.unplaced.length > 0 && (
            <div className="mt-4 rounded-md border border-danger/30 bg-danger/5 p-3">
              <p className="text-sm font-medium text-danger">{t("unplacedWarning")}</p>
              <ul className="mt-1 list-disc pl-5 text-sm text-danger">
                {result.unplaced.map((u, i) => (
                  <li key={i}>{u.label} #{u.instance_index} — {u.reason}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="mt-3 text-xs text-text-secondary">
            <Link href={`/cut-optimization/history/${result.id}`} className="text-primary hover:underline">
              {t("viewInHistory")}
            </Link>
          </p>
        </Card>
      )}

      {!result && effectiveLength && effectiveWidth && parseFloat(effectiveLength) > 0 && parseFloat(effectiveWidth) > 0 && (
        <Card>
          <CardHeader title={t("slabPreview")} />
          <SlabLayoutSvg slabLengthMm={parseFloat(effectiveLength)} slabWidthMm={parseFloat(effectiveWidth)} placements={[]} />
        </Card>
      )}
    </div>
  );
}
