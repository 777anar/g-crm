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

export function useEntityStatusLabel() {
  const t = useTranslations("catalog.entityStatus");
  return (status: string) => t(status);
}

export function useSlabStatusLabel() {
  const t = useTranslations("catalog.slabStatus");
  return (status: string) => t(status);
}

export function useImageTypeLabel() {
  const t = useTranslations("catalog.imageType");
  return (type: string) => t(type);
}

export function useDocumentTypeLabel() {
  const t = useTranslations("catalog.documentType");
  return (type: string) => t(type);
}
