"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { PurchasingTabs } from "@/components/purchasing-tabs";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { TextField } from "@/components/ui/field";
import { addSupplierContact, deleteSupplierContact, getSupplier, getSupplierMetrics, listSupplierContacts } from "@/lib/api/purchasing";
import type { Supplier, SupplierContact, SupplierMetrics } from "@/lib/types";
import { usePermission } from "@/lib/permissions";
import { useToast } from "@/components/ui/toast";

export default function SupplierDetail() {
  const { id } = useParams<{id:string}>(); const t = useTranslations("purchasing"); const toast = useToast();
  const canWrite = usePermission("purchasing:suppliers:write");
  const [supplier,setSupplier]=useState<Supplier|null>(null); const [contacts,setContacts]=useState<SupplierContact[]>([]);
  const [metrics,setMetrics]=useState<SupplierMetrics|null>(null); const [name,setName]=useState("");
  const [email,setEmail]=useState(""); const [phone,setPhone]=useState("");
  const load=useCallback(()=>Promise.all([getSupplier(id).then(setSupplier),listSupplierContacts(id).then(setContacts),getSupplierMetrics(id).then(setMetrics)]),[id]);
  useEffect(()=>{load().catch(e=>toast.error(e.message));},[load,toast]);
  if(!supplier)return <p>{t("loading")}</p>;
  return <div className="flex flex-col gap-4"><PurchasingTabs/><div><h1 className="text-xl font-semibold">{supplier.name}</h1><p className="text-sm text-text-secondary">{supplier.tax_id??t("noTaxId")} · {supplier.payment_terms_days} {t("days")}</p></div>
    {metrics&&<div className="grid gap-3 sm:grid-cols-4">{[["totalSpend",metrics.total_spend],["fillRate",`${metrics.fill_rate}%`],["onTimeRate",`${metrics.on_time_delivery_rate}%`],["outstandingPayables",metrics.outstanding_amount]].map(([k,v])=><Card key={k}><p className="text-xs text-text-secondary">{t(k)}</p><p className="text-xl font-semibold">{v}</p></Card>)}</div>}
    <Card><CardHeader title={t("supplierContacts")}/>{contacts.map(c=><div key={c.id} className="flex justify-between border-b border-border py-2"><span>{c.name} {c.is_primary&&`(${t("primary")})`} · {c.email??c.phone??"—"}</span>{canWrite&&<Button variant="secondary" onClick={async()=>{await deleteSupplierContact(id,c.id);await load();}}>{t("remove")}</Button>}</div>)}
      {canWrite&&<form className="mt-3 grid gap-2 sm:grid-cols-4" onSubmit={async e=>{e.preventDefault();await addSupplierContact(id,{name,email:email||undefined,phone:phone||undefined,is_primary:contacts.length===0});setName("");setEmail("");setPhone("");await load();}}><TextField label={t("name")} value={name} onChange={e=>setName(e.target.value)} required/><TextField label={t("email")} value={email} onChange={e=>setEmail(e.target.value)}/><TextField label={t("phone")} value={phone} onChange={e=>setPhone(e.target.value)}/><Button type="submit">{t("addContact")}</Button></form>}
    </Card></div>;
}
