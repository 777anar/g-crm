"use client";
import { useTranslations } from "next-intl";
import { SectionTabs } from "@/components/ui/section-tabs";
import { purchasingTabs } from "@/lib/api/purchasing";
export function PurchasingTabs(){const t=useTranslations("purchasing");return <SectionTabs items={purchasingTabs.map(x=>({label:t(x.labelKey),href:x.href}))}/>;}
