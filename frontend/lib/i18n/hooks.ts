"use client";

import { useTranslations } from "next-intl";

/** Translates a lead source channel code (e.g. "instagram") to its display
 * label, for contexts where a <Badge> can't be used directly (e.g. <option>
 * elements in a <select>). */
export function useLeadChannelLabel() {
  const t = useTranslations("leadChannel");
  return (channel: string) => t(channel);
}

export function useLeadStatusLabel() {
  const t = useTranslations("leadStatus");
  return (status: string) => t(status);
}

export function useCustomerTypeLabel() {
  const t = useTranslations("customerType");
  return (type: string) => t(type);
}

/** Translates a stone-industry sales pipeline status code (e.g.
 * "in_production") to its display label. */
export function useCustomerStatusLabel() {
  const t = useTranslations("customerStatus");
  return (status: string) => t(status);
}
