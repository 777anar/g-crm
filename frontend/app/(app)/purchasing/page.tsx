"use client";
import { useEffect,useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { PurchasingTabs } from "@/components/purchasing-tabs";
import { Card,CardHeader } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { getProcurementDashboard } from "@/lib/api/purchasing";
import type { ProcurementDashboard } from "@/lib/types";
export default function PurchasingDashboard(){const t=useTranslations("purchasing");const [d,setD]=useState<ProcurementDashboard|null>(null);const [error,setError]=useState("");useEffect(()=>{getProcurementDashboard().then(setD).catch(e=>setError(e.message))},[]);return <div className="flex flex-col gap-4"><PurchasingTabs/><div><h1 className="text-xl font-semibold">{t("dashboardTitle")}</h1><p className="text-sm text-text-secondary">{t("dashboardSubtitle")}</p></div>{error&&<p className="text-danger">{error}</p>}{!d?<TableSkeleton rows={3} columns={4}/>:<><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><StatCard label={t("activeSuppliers")} value={d.supplier_count}/><StatCard label={t("openRfqs")} value={d.open_rfqs}/><StatCard label={t("pendingApprovals")} value={d.pending_approvals}/><StatCard label={t("outstandingPayables")} value={`AZN ${Number(d.outstanding_payables).toFixed(2)}`}/></div><Card><CardHeader title={t("recentOrders")}/><div className="divide-y divide-border">{d.recent_orders.map(o=><Link key={o.id} href={`/purchasing/orders/${o.id}`} className="flex justify-between py-2 text-sm hover:text-primary"><span className="font-mono">{o.po_number}</span><span>{t(o.status)} · {o.currency} {Number(o.total_amount).toFixed(2)}</span></Link>)}</div></Card></>}</div>}
