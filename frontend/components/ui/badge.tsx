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

const PROJECT_STATUS_TONE: Record<string, Tone> = {
  active: "info",
  completed: "success",
  cancelled: "danger",
};

export function ProjectStatusBadge({ status }: { status: string }) {
  const t = useTranslations("sales");
  return <Badge tone={PROJECT_STATUS_TONE[status] ?? "neutral"}>{t(status as any)}</Badge>;
}

const QUOTE_STATUS_TONE: Record<string, Tone> = {
  draft: "neutral",
  sent: "info",
  negotiation: "warning",
  accepted: "success",
  rejected: "danger",
  expired: "neutral",
};

export function QuoteStatusBadge({ status }: { status: string }) {
  const t = useTranslations("sales");
  return <Badge tone={QUOTE_STATUS_TONE[status] ?? "neutral"}>{t(status as any)}</Badge>;
}

// Order lifecycle: cool grey while queued, warm while shop-floor work is
// active, info while in transit/measuring, green once installed/complete,
// red for the one terminal failure state -- same rationale as
// CUSTOMER_STATUS_TONE above.
const ORDER_STATUS_TONE: Record<string, Tone> = {
  waiting: "neutral",
  measuring: "info",
  approved_for_production: "info",
  in_production: "warning",
  ready: "warning",
  delivered: "info",
  installed: "success",
  completed: "success",
  cancelled: "danger",
};

export function OrderStatusBadge({ status }: { status: string }) {
  const t = useTranslations("orders");
  return <Badge tone={ORDER_STATUS_TONE[status] ?? "neutral"}>{t(status as any)}</Badge>;
}

const WORK_ORDER_STATUS_TONE: Record<string, Tone> = {
  queued: "neutral",
  cutting: "warning",
  polishing: "warning",
  quality_check: "info",
  completed: "success",
  cancelled: "danger",
};

export function WorkOrderStatusBadge({ status }: { status: string }) {
  const t = useTranslations("production");
  return <Badge tone={WORK_ORDER_STATUS_TONE[status] ?? "neutral"}>{t(status as any)}</Badge>;
}

const INSTALLATION_JOB_STATUS_TONE: Record<string, Tone> = {
  scheduled: "neutral",
  en_route: "info",
  in_progress: "warning",
  completed: "success",
  cancelled: "danger",
};

export function InstallationJobStatusBadge({ status }: { status: string }) {
  const t = useTranslations("installation");
  return <Badge tone={INSTALLATION_JOB_STATUS_TONE[status] ?? "neutral"}>{t(status as any)}</Badge>;
}

const CREW_STATUS_TONE: Record<string, Tone> = {
  active: "success",
  inactive: "neutral",
};

export function CrewStatusBadge({ status }: { status: string }) {
  const t = useTranslations("installation");
  return <Badge tone={CREW_STATUS_TONE[status] ?? "neutral"}>{t(status as any)}</Badge>;
}

const INVOICE_STATUS_TONE: Record<string, Tone> = {
  draft: "neutral",
  sent: "info",
  partially_paid: "warning",
  paid: "success",
  overdue: "danger",
  cancelled: "danger",
};

export function InvoiceStatusBadge({ status }: { status: string }) {
  const t = useTranslations("finance");
  return <Badge tone={INVOICE_STATUS_TONE[status] ?? "neutral"}>{t(status as any)}</Badge>;
}
