"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { createProductionStage, listProductionStages, updateProductionStage } from "@/lib/api/production";
import type { ProductionStage } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { usePermission } from "@/lib/permissions";

export default function ProductionStagesPage() {
  const t = useTranslations("production");
  const tNav = useTranslations("nav");
  const canWrite = usePermission("production:write");
  const [stages, setStages] = useState<ProductionStage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [reorderingId, setReorderingId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const res = await listProductionStages();
      setStages(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }, [t]);

  useEffect(() => {
    setStages(null);
    reload();
  }, [reload]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createProductionStage(name);
      setName("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleActive(stage: ProductionStage) {
    try {
      const updated = await updateProductionStage(stage.id, { is_active: !stage.is_active });
      setStages((prev) => prev?.map((s) => (s.id === updated.id ? updated : s)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("updateFailed"));
    }
  }

  async function handleRename(stage: ProductionStage) {
    if (!renameValue || renameValue === stage.name) {
      setRenamingId(null);
      return;
    }
    try {
      const updated = await updateProductionStage(stage.id, { name: renameValue });
      setStages((prev) => prev?.map((s) => (s.id === updated.id ? updated : s)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("updateFailed"));
    } finally {
      setRenamingId(null);
    }
  }

  async function handleMove(index: number, direction: -1 | 1) {
    if (!stages) return;
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= stages.length) return;
    const current = stages[index];
    const target = stages[targetIndex];

    setReorderingId(current.id);
    try {
      const [updatedCurrent, updatedTarget] = await Promise.all([
        updateProductionStage(current.id, { sort_order: target.sort_order }),
        updateProductionStage(target.id, { sort_order: current.sort_order }),
      ]);
      setStages((prev) => {
        if (!prev) return prev;
        const next = prev.map((s) => {
          if (s.id === updatedCurrent.id) return updatedCurrent;
          if (s.id === updatedTarget.id) return updatedTarget;
          return s;
        });
        return [...next].sort((a, b) => a.sort_order - b.sort_order);
      });
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("updateFailed"));
    } finally {
      setReorderingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("production"), href: "/production" }, { label: t("stagesTitle") }]} />

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("stagesTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("stagesSubtitle")}</p>
      </div>

      {canWrite && (
      <Card>
        <CardHeader title={t("createStage")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
          <TextField label={t("stageName")} value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !name}>
              {submitting ? t("creating") : t("createStage")}
            </Button>
          </div>
        </form>
      </Card>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {stages === null && !error && <TableSkeleton rows={8} columns={3} />}

      {stages && stages.length > 0 && (
        <div className={tableScrollShellClass}>
          <table className="w-full text-left text-sm">
            <thead className={stickyTheadClass}>
              <tr>
                <th className="px-4 py-2 font-medium">{t("stageOrder")}</th>
                <th className="px-4 py-2 font-medium">{t("stageName")}</th>
                <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {stages.map((stage, index) => (
                <tr key={stage.id} className="border-b border-border last:border-0 hover:bg-bg">
                  <td className="px-4 py-2 text-text-secondary">
                    <div className="flex items-center gap-1">
                      <span>{stage.sort_order + 1}</span>
                      {canWrite && (
                        <span className="flex flex-col">
                          <button
                            className="leading-none text-text-secondary hover:text-text-primary disabled:opacity-30"
                            aria-label={t("moveStageUp")}
                            disabled={index === 0 || reorderingId !== null}
                            onClick={() => handleMove(index, -1)}
                          >
                            ▲
                          </button>
                          <button
                            className="leading-none text-text-secondary hover:text-text-primary disabled:opacity-30"
                            aria-label={t("moveStageDown")}
                            disabled={index === stages.length - 1 || reorderingId !== null}
                            onClick={() => handleMove(index, 1)}
                          >
                            ▼
                          </button>
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2 font-medium text-text-primary">
                    {renamingId === stage.id ? (
                      <input
                        autoFocus
                        className="w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => handleRename(stage)}
                        onKeyDown={(e) => e.key === "Enter" && handleRename(stage)}
                      />
                    ) : canWrite ? (
                      <button
                        className="text-left hover:underline"
                        onClick={() => {
                          setRenamingId(stage.id);
                          setRenameValue(stage.name);
                        }}
                      >
                        {stage.name}
                      </button>
                    ) : (
                      stage.name
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={stage.is_active ? "success" : "neutral"}>
                      {stage.is_active ? t("stageActive") : t("stageHidden")}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {canWrite && (
                      <Button variant="secondary" onClick={() => handleToggleActive(stage)}>
                        {stage.is_active ? t("stageHidden") : t("stageActive")}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
