"use client";

import { useTranslations } from "next-intl";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-bg text-text-secondary border-border",
  success: "bg-success/10 text-success border-success/30",
  warning: "bg-warning/10 text-warning border-warning/30",
  danger: "bg-danger/10 text-danger border-danger/30",
  info: "bg-info/10 text-info border-info/30",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}>
      {children}
    </span>
  );
}

const LEAD_STATUS_TONE: Record<string, Tone> = {
  new: "info",
  contacted: "warning",
  qualified: "warning",
  converted: "success",
  disqualified: "danger",
};

export function LeadStatusBadge({ status }: { status: string }) {
  const t = useTranslations("leadStatus");
  return <Badge tone={LEAD_STATUS_TONE[status] ?? "neutral"}>{t(status)}</Badge>;
}

export function LeadChannelBadge({ channel }: { channel: string }) {
  const t = useTranslations("leadChannel");
  return <Badge tone="info">{t(channel)}</Badge>;
}

export function CustomerArchivedBadge({ archived }: { archived: boolean }) {
  const t = useTranslations("customers");
  return archived ? <Badge tone="danger">{t("statusArchived")}</Badge> : <Badge tone="success">{t("statusActive")}</Badge>;
}

// Stone-industry sales pipeline status tones: cool grey while unqualified,
// warm while a quote is in motion, green once money/installation is
// locked in, red for the one terminal failure state.
const CUSTOMER_STATUS_TONE: Record<string, Tone> = {
  new_inquiry: "neutral",
  contacted: "neutral",
  measurement_scheduled: "info",
  measurement_completed: "info",
  preparing_quote: "warning",
  quote_sent: "warning",
  waiting_for_decision: "warning",
  approved: "success",
  payment_received: "success",
  in_production: "info",
  installation_scheduled: "info",
  installed: "success",
  completed: "success",
  lost: "danger",
};

export function CustomerStatusBadge({ status }: { status: string }) {
  const t = useTranslations("customerStatus");
  return <Badge tone={CUSTOMER_STATUS_TONE[status] ?? "neutral"}>{t(status)}</Badge>;
}

export function EntityStatusBadge({ status }: { status: string }) {
  const t = useTranslations("catalog.entityStatus");
  return <Badge tone={status === "active" ? "success" : "neutral"}>{t(status)}</Badge>;
}

const SLAB_STATUS_TONE: Record<string, Tone> = {
  available: "success",
  reserved: "warning",
  sold: "info",
  in_production: "info",
  scrap: "danger",
};

export function SlabStatusBadge({ status }: { status: string }) {
  const t = useTranslations("catalog.slabStatus");
  return <Badge tone={SLAB_STATUS_TONE[status] ?? "neutral"}>{t(status)}</Badge>;
}
