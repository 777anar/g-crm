"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { getCutOptimizationRun } from "@/lib/api/cut-optimization";
import type { CutOptimizationRun } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, CardHeader } from "@/components/ui/card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { SlabLayoutSvg } from "@/components/cut-optimization/slab-layout-svg";

export default function CutOptimizationRunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("cutOptimization");
  const tNav = useTranslations("nav");

  const [run, setRun] = useState<CutOptimizationRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCutOptimizationRun(id)
      .then(setRun)
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [id, t]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!run) return <TableSkeleton rows={5} columns={4} />;

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        items={[
          { label: tNav("cutOptimization"), href: "/cut-optimization" },
          { label: t("historyLink"), href: "/cut-optimization/history" },
          { label: `${run.slab_length_mm}×${run.slab_width_mm}mm` },
        ]}
      />

      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold text-text-primary">
          {run.slab_length_mm}×{run.slab_width_mm}mm
        </h1>
        <Badge tone={run.source === "offcut_recommendation" ? "info" : "neutral"}>
          {t(`source_${run.source}` as Parameters<typeof t>[0])}
        </Badge>
      </div>
      <p className="text-xs text-text-secondary">{t("created")}: {formatDateTime(run.created_at)}</p>

      <Card>
        <CardHeader title={t("resultSection")} />
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
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

        <SlabLayoutSvg
          slabLengthMm={parseFloat(run.slab_length_mm)}
          slabWidthMm={parseFloat(run.slab_width_mm)}
          placements={run.placements}
        />

        {run.unplaced.length > 0 && (
          <div className="mt-4 rounded-md border border-danger/30 bg-danger/5 p-3">
            <p className="text-sm font-medium text-danger">{t("unplacedWarning")}</p>
            <ul className="mt-1 list-disc pl-5 text-sm text-danger">
              {run.unplaced.map((u, i) => (
                <li key={i}>{u.label} #{u.instance_index} — {u.reason}</li>
              ))}
            </ul>
          </div>
        )}
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
