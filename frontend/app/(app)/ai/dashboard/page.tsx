"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getAIDashboard, listRecommendations, analyzeLead, suggestTasks } from "@/lib/api/ai";
import { listLeads } from "@/lib/api/crm";
import type { AIDashboard, AIRecommendation, Lead } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { StatusBarList } from "@/components/ui/charts";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { StatCardSkeleton, TableSkeleton } from "@/components/ui/skeleton";
import { RecommendationCard } from "@/components/recommendation-card";
import { ApiRequestError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";

const SCORE_BUCKET_ORDER = ["0-25", "26-50", "51-75", "76-100"];

export default function AIDashboardPage() {
  const t = useTranslations("ai");
  const tCommon = useTranslations("common");

  const [dashboard, setDashboard] = useState<AIDashboard | null>(null);
  const [pendingById, setPendingById] = useState<Record<string, AIRecommendation>>({});
  const [error, setError] = useState<string | null>(null);

  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLeadId, setSelectedLeadId] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    Promise.all([getAIDashboard(), listRecommendations({ status: "pending", limit: 100 })])
      .then(([dash, recRes]) => {
        setDashboard(dash);
        const map: Record<string, AIRecommendation> = {};
        recRes.items.forEach((r) => { map[r.id] = r; });
        setPendingById(map);
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    listLeads({ limit: 100 })
      .then((r) => setLeads(r.items.filter((l) => l.status === "new" || l.status === "contacted" || l.status === "qualified")))
      .catch(() => {});
  }, []);

  function handleReviewed(updated: AIRecommendation) {
    setPendingById((prev) => {
      const next = { ...prev };
      if (updated.status === "pending") next[updated.id] = updated;
      else delete next[updated.id];
      return next;
    });
    load();
  }

  async function handleAnalyzeLead() {
    if (!selectedLeadId) return;
    setBusy(true);
    try {
      await analyzeLead(selectedLeadId);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleSuggestTasks() {
    setBusy(true);
    try {
      await suggestTasks();
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (!dashboard && !error) {
    return (
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
        </div>
        <TableSkeleton rows={5} columns={3} />
      </div>
    );
  }

  if (error || !dashboard) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  const scoreDistribution = SCORE_BUCKET_ORDER.map((label) => ({
    label,
    count: dashboard.lead_score_distribution[label] ?? 0,
  }));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("dashboardTitle")}</h1>
        <p className="text-sm text-text-secondary">{t("dashboardSubtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("runAnalysis")} />
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs text-text-secondary">{t("analyzeLead")}</label>
            <select
              value={selectedLeadId}
              onChange={(e) => setSelectedLeadId(e.target.value)}
              className="mt-0.5 block rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text-primary"
            >
              <option value="">{t("selectLead")}</option>
              {leads.map((l) => (
                <option key={l.id} value={l.id}>{l.full_name}</option>
              ))}
            </select>
          </div>
          <Button onClick={handleAnalyzeLead} disabled={busy || !selectedLeadId}>{t("analyzeLead")}</Button>
          <Button variant="secondary" onClick={handleSuggestTasks} disabled={busy}>{t("suggestTasks")}</Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={t("statAvgWinProbability")}
          value={dashboard.avg_win_probability !== null ? `${Math.round(dashboard.avg_win_probability * 100)}%` : tCommon("dash")}
          tone="primary"
        />
        <StatCard label={t("statActivePipeline")} value={dashboard.pipeline_health.active_pipeline_count} tone="info" />
        <StatCard label={t("statStalledPipeline")} value={`${dashboard.pipeline_health.stalled_pct}%`} tone="warning" />
        <StatCard
          label={t("statAcceptanceRate")}
          value={dashboard.usage_stats.acceptance_rate !== null ? `${Math.round(dashboard.usage_stats.acceptance_rate * 100)}%` : tCommon("dash")}
          tone="success"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader title={t("leadScoreDistribution")} />
          <StatusBarList data={scoreDistribution} emptyLabel={t("noDataYet")} />
        </Card>
        <Card>
          <CardHeader title={t("usageStatistics")} />
          <dl className="flex flex-col gap-2 text-sm">
            <div className="flex justify-between"><dt className="text-text-secondary">{t("totalRecommendations")}</dt><dd className="text-text-primary">{dashboard.usage_stats.total_recommendations}</dd></div>
            {Object.entries(dashboard.usage_stats.provider_counts).map(([provider, count]) => (
              <div key={provider} className="flex justify-between"><dt className="text-text-secondary">{provider}</dt><dd className="text-text-primary">{count}</dd></div>
            ))}
            <div className="flex justify-between"><dt className="text-text-secondary">{t("avgExecutionTime")}</dt><dd className="text-text-primary">{dashboard.usage_stats.avg_execution_time_ms ?? tCommon("dash")} ms</dd></div>
          </dl>
        </Card>
        <Card>
          <CardHeader title={t("pipelineHealth")} />
          <dl className="flex flex-col gap-2 text-sm">
            <div className="flex justify-between"><dt className="text-text-secondary">{t("statActivePipeline")}</dt><dd className="text-text-primary">{dashboard.pipeline_health.active_pipeline_count}</dd></div>
            <div className="flex justify-between"><dt className="text-text-secondary">{t("stalledCustomers")}</dt><dd className="text-text-primary">{dashboard.pipeline_health.stalled_count}</dd></div>
          </dl>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader title={t("atRiskCustomers")} />
          {dashboard.at_risk_customers.length === 0 ? (
            <EmptyState title={t("noAtRiskYet")} />
          ) : (
            <div className="flex flex-col gap-2">
              {dashboard.at_risk_customers.map((item) => {
                const rec = pendingById[item.recommendation_id];
                return rec ? <RecommendationCard key={rec.id} recommendation={rec} onReviewed={handleReviewed} /> : null;
              })}
            </div>
          )}
        </Card>
        <Card>
          <CardHeader title={t("followUpRecommendations")} />
          {dashboard.follow_up_recommendations.length === 0 ? (
            <EmptyState title={t("noFollowUpsYet")} />
          ) : (
            <div className="flex flex-col gap-2">
              {dashboard.follow_up_recommendations.map((item) => {
                const rec = pendingById[item.recommendation_id];
                return rec ? <RecommendationCard key={rec.id} recommendation={rec} onReviewed={handleReviewed} /> : null;
              })}
            </div>
          )}
        </Card>
        <Card>
          <CardHeader title={t("dailyRecommendations")} />
          {dashboard.daily_recommendations.length === 0 ? (
            <EmptyState title={t("noDailyRecommendationsYet")} />
          ) : (
            <div className="flex flex-col gap-2">
              {dashboard.daily_recommendations.map((item) => {
                const rec = pendingById[item.recommendation_id];
                return rec ? <RecommendationCard key={rec.id} recommendation={rec} onReviewed={handleReviewed} /> : null;
              })}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <CardHeader title={t("recentActivity")} />
        {dashboard.recent_activity.length === 0 ? (
          <EmptyState title={t("noActivityYet")} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border text-text-secondary">
                <tr>
                  <th className="px-2 py-1 font-medium">{t("tableType")}</th>
                  <th className="px-2 py-1 font-medium">{t("tableSummary")}</th>
                  <th className="px-2 py-1 font-medium">{t("tableStatus")}</th>
                  <th className="px-2 py-1 font-medium">{t("tableProvider")}</th>
                  <th className="px-2 py-1 font-medium">{t("tableWhen")}</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_activity.map((activity) => (
                  <tr key={activity.recommendation_id} className="border-b border-border last:border-0">
                    <td className="px-2 py-1 text-text-primary">{t(`type_${activity.recommendation_type}` as any)}</td>
                    <td className="px-2 py-1 text-text-secondary">{activity.summary ?? tCommon("dash")}</td>
                    <td className="px-2 py-1 text-text-secondary">{t(`status_${activity.status}` as any)}</td>
                    <td className="px-2 py-1 text-text-secondary">{activity.provider}</td>
                    <td className="px-2 py-1 text-text-secondary">{formatDateTime(activity.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
