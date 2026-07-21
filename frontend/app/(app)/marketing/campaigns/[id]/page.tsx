"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  getCampaign,
  getCampaignPerformance,
  updateCampaign,
  updateCampaignStatus,
} from "@/lib/api/marketing";
import type { Campaign, CampaignPerformance } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { CampaignStatusBadge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat-card";
import { TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { useLeadChannelLabel } from "@/lib/i18n/hooks";
import { formatDate } from "@/lib/format";

const MANUAL_NEXT_STATUS: Record<string, string | null> = {
  draft: "active",
  active: "completed",
  completed: null,
  cancelled: null,
};

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("marketing");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");
  const channelLabel = useLeadChannelLabel();
  const toast = useToast();

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [performance, setPerformance] = useState<CampaignPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);

  const [notes, setNotes] = useState("");
  const [budget, setBudget] = useState("");
  const [savingDetails, setSavingDetails] = useState(false);

  const reload = useCallback(async () => {
    const [c, perf] = await Promise.all([getCampaign(id), getCampaignPerformance(id)]);
    setCampaign(c);
    setNotes(c.notes ?? "");
    setBudget(c.budget ?? "");
    setPerformance(perf);
    setLoading(false);
  }, [id]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleAdvance() {
    if (!campaign) return;
    const next = MANUAL_NEXT_STATUS[campaign.status];
    if (!next) return;
    setTransitioning(true);
    try {
      await updateCampaignStatus(id, next);
      toast.success(t("statusUpdated"));
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleCancel() {
    setTransitioning(true);
    try {
      await updateCampaignStatus(id, "cancelled");
      setCancelMode(false);
      toast.success(t("statusUpdated"));
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleSaveDetails() {
    setSavingDetails(true);
    try {
      await updateCampaign(id, { notes, budget: budget || undefined });
      toast.success(t("detailsSaved"));
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setSavingDetails(false);
    }
  }

  if (loading || !campaign) return <TableSkeleton rows={5} columns={4} />;

  const isTerminal = campaign.status === "completed" || campaign.status === "cancelled";
  const nextStatus = MANUAL_NEXT_STATUS[campaign.status];
  const isEditable = campaign.status !== "completed" && campaign.status !== "cancelled";

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("campaigns"), href: "/marketing/campaigns" }, { label: campaign.name }]} />

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-text-primary">{campaign.name}</h1>
            <CampaignStatusBadge status={campaign.status} />
          </div>
          <p className="mt-1 text-xs text-text-secondary">{channelLabel(campaign.channel)}</p>
        </div>
        {!isTerminal && (
          <div className="flex gap-2">
            {nextStatus && (
              <Button onClick={handleAdvance} disabled={transitioning}>
                {transitioning ? t("saving") : `→ ${t(nextStatus as any)}`}
              </Button>
            )}
            {!cancelMode && (
              <Button variant="secondary" onClick={() => setCancelMode(true)}>
                {t("cancelCampaign")}
              </Button>
            )}
          </div>
        )}
      </div>

      {cancelMode && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="mb-2 text-sm text-danger">{t("confirmCancel")}</p>
          <div className="flex gap-2">
            <Button onClick={handleCancel} disabled={transitioning}>
              {t("cancelCampaign")}
            </Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>
              {tCommon("cancel")}
            </Button>
          </div>
        </Card>
      )}

      {performance && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("leadsCount")} value={performance.leads_count} />
          <StatCard label={t("convertedCount")} value={performance.converted_count} tone="success" />
          <StatCard label={t("conversionRate")} value={`${(performance.conversion_rate * 100).toFixed(1)}%`} tone="info" />
          <StatCard
            label={t("attributedRevenue")}
            value={`${campaign.currency} ${parseFloat(performance.attributed_revenue).toFixed(2)}`}
            tone="primary"
          />
        </div>
      )}

      <Card>
        <CardHeader title={t("campaignDetails")} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <TextField label={t("budget")} type="number" min="0" step="0.01" value={budget} onChange={(e) => setBudget(e.target.value)} disabled={!isEditable} />
          <div className="sm:col-span-2">
            <TextField label={t("notes")} value={notes} onChange={(e) => setNotes(e.target.value)} disabled={!isEditable} />
          </div>
        </div>
        {isEditable && (
          <div className="mt-3 flex justify-end">
            <Button variant="secondary" loading={savingDetails} onClick={handleSaveDetails}>
              {tCommon("save")}
            </Button>
          </div>
        )}
      </Card>

      <p className="text-xs text-text-secondary">
        {t("created")}: {formatDate(campaign.created_at)}
      </p>
    </div>
  );
}
