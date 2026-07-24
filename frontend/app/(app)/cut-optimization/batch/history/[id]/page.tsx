"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { exportBatchRunDxf, getBatchCutOptimizationRun } from "@/lib/api/cut-optimization";
import type { CutOptimizationBatchRun } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { SlabLayoutSvg } from "@/components/cut-optimization/slab-layout-svg";

export default function BatchCutOptimizationRunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("cutOptimization");
  const tNav = useTranslations("nav");

  const [run, setRun] = useState<CutOptimizationBatchRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    getBatchCutOptimizationRun(id)
      .then(setRun)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [id, t]);

  async function handleExport() {
    setExporting(true);
    try {
      await exportBatchRunDxf(id);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("exportFailed"));
    } finally {
      setExporting(false);
    }
  }

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!run) return <TableSkeleton rows={5} columns={4} />;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        items={[
          { label: tNav("cutOptimization"), href: "/cut-optimization" },
          { label: t("batchTitle"), href: "/cut-optimization/batch" },
          { label: t("historyLink"), href: "/cut-optimization/batch/history" },
          { label: `${run.slabs_used_count} ${t("slabsUsed")}` },
        ]}
      />

      <h1 className="text-xl font-semibold text-text-primary">
        {run.slabs_used_count} {t("slabsUsed")}
      </h1>
      <p className="text-xs text-text-secondary">{t("created")}: {formatDateTime(run.created_at)}</p>

      <Card>
        <CardHeader
          title={t("resultSection")}
          action={
            <Button variant="secondary" onClick={handleExport} loading={exporting}>
              {t("exportDxf")}
            </Button>
          }
        />
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
          <div>
            <p className="text-xs text-text-secondary">{t("slabsUsed")}</p>
            <p className="text-lg font-semibold text-text-primary">{run.slabs_used_count}</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("utilization")}</p>
            <p className="text-lg font-semibold text-text-primary">{run.utilization_pct}%</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("wasteArea")}</p>
            <p className="text-lg font-semibold text-text-primary">{run.waste_area_m2} m²</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("placedArea")}</p>
            <p className="text-lg font-semibold text-text-primary">{run.placed_area_m2} m²</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary">{t("totalArea")}</p>
            <p className="text-lg font-semibold text-text-primary">{run.total_area_m2} m²</p>
          </div>
        </div>

        {run.unplaced.length > 0 && (
          <div className="mb-4 rounded-md border border-danger/30 bg-danger/5 p-3">
            <p className="text-sm font-medium text-danger">{t("unplacedWarning")}</p>
            <ul className="mt-1 list-disc pl-5 text-sm text-danger">
              {run.unplaced.map((u, i) => (
                <li key={i}>{u.label} #{u.instance_index} — {u.reason}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex flex-col gap-4">
          {run.slabs.map((slab) => (
            <div key={slab.slab_ref}>
              <p className="mb-2 text-sm font-medium text-text-primary">
                {slab.slab_ref} ({slab.length_mm}×{slab.width_mm}mm)
              </p>
              <SlabLayoutSvg
                slabLengthMm={parseFloat(slab.length_mm)}
                slabWidthMm={parseFloat(slab.width_mm)}
                placements={run.placements.filter((p) => p.slab_ref === slab.slab_ref)}
              />
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title={t("piecesSection")} />
        <table className="w-full text-left text-sm">
          <thead className="text-text-secondary">
            <tr>
              <th className="px-2 py-1 font-medium">{t("pieceLabel")}</th>
              <th className="px-2 py-1 font-medium">{t("pieceLength")}</th>
              <th className="px-2 py-1 font-medium">{t("pieceWidth")}</th>
              <th className="px-2 py-1 font-medium">{t("pieceQuantity")}</th>
            </tr>
          </thead>
          <tbody>
            {run.pieces.map((p, i) => (
              <tr key={i} className="border-t border-border">
                <td className="px-2 py-1 text-text-primary">{p.label}</td>
                <td className="px-2 py-1 text-text-secondary">{p.length_mm}mm</td>
                <td className="px-2 py-1 text-text-secondary">{p.width_mm}mm</td>
                <td className="px-2 py-1 text-text-secondary">{p.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
