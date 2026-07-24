"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { reviewRecommendation } from "@/lib/api/ai";
import type { AIRecommendation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/format";

const STATUS_TONE: Record<string, "neutral" | "success" | "danger" | "warning"> = {
  pending: "warning",
  accepted: "success",
  rejected: "danger",
  edited: "neutral",
};

/** Renders one AIRecommendation with Accept/Reject/Edit actions -- the one
 * UI surface every AI feature (Dashboard, Leads, Inbox, Tasks) reuses, so
 * "AI never performs business actions automatically" reads the same way
 * everywhere: reviewing a card only ever changes its own status. */
export function RecommendationCard({
  recommendation,
  onReviewed,
}: {
  recommendation: AIRecommendation;
  onReviewed?: (updated: AIRecommendation) => void;
}) {
  const t = useTranslations("ai");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(() => JSON.stringify(recommendation.response, null, 2));
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const isPending = recommendation.status === "pending";

  async function handleDecision(decision: "accept" | "reject") {
    setBusy(true);
    setError(null);
    try {
      const updated = await reviewRecommendation(recommendation.id, decision);
      onReviewed?.(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("reviewFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveEdit() {
    setBusy(true);
    setError(null);
    try {
      const parsed = JSON.parse(editText);
      const updated = await reviewRecommendation(recommendation.id, "edit", parsed);
      setEditing(false);
      onReviewed?.(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("invalidJson"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          {t(`type_${recommendation.recommendation_type}` as Parameters<typeof t>[0])}
        </span>
        <Badge tone={STATUS_TONE[recommendation.status] ?? "neutral"}>{t(`status_${recommendation.status}` as Parameters<typeof t>[0])}</Badge>
      </div>

      <p className="text-sm text-text-primary">{recommendation.summary}</p>

      <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
        <span>{t("provider")}: {recommendation.provider}{recommendation.model ? ` (${recommendation.model})` : ""}</span>
        {recommendation.confidence_score !== null && (
          <span>{t("confidence")}: {Math.round(recommendation.confidence_score * 100)}%</span>
        )}
        <button className="text-primary hover:underline" onClick={() => setShowDetails((v) => !v)}>
          {showDetails ? t("hideDetails") : t("showDetails")}
        </button>
      </div>

      {showDetails && (
        <div className="flex flex-col gap-2">
          <div>
            <p className="mb-1 text-xs font-medium text-text-secondary">{t("promptLabel")}</p>
            <pre className="max-h-32 overflow-auto rounded bg-bg p-2 text-xs text-text-secondary">
              {recommendation.prompt}
            </pre>
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-text-secondary">{t("responseLabel")}</p>
            <pre className="max-h-40 overflow-auto rounded bg-bg p-2 text-xs text-text-secondary">
              {JSON.stringify(recommendation.response, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {editing && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-text-secondary">{t("editJsonHint")}</p>
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={6}
            className="rounded-md border border-border bg-bg px-2 py-1 font-mono text-xs text-text-primary"
          />
          <div className="flex gap-2">
            <Button onClick={handleSaveEdit} disabled={busy}>{t("saveEdit")}</Button>
            <Button variant="secondary" onClick={() => setEditing(false)}>{t("cancelEdit")}</Button>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-danger">{error}</p>}

      {isPending && !editing && (
        <div className="flex gap-2">
          <Button onClick={() => handleDecision("accept")} disabled={busy}>{t("accept")}</Button>
          <Button variant="secondary" onClick={() => handleDecision("reject")} disabled={busy}>{t("reject")}</Button>
          <Button variant="secondary" onClick={() => setEditing(true)} disabled={busy}>{t("edit")}</Button>
        </div>
      )}

      {!isPending && (
        <p className="text-xs text-text-secondary">
          {t("reviewedAt", { date: recommendation.reviewed_at ? formatDateTime(recommendation.reviewed_at) : "" })}
        </p>
      )}
    </div>
  );
}
