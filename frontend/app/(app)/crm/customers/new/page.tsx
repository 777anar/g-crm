"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { createCustomer } from "@/lib/api/crm";
import { listCompanyUsers } from "@/lib/api/companies";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { CUSTOMER_STATUSES, CUSTOMER_TYPES, LEAD_SOURCE_CHANNELS, type CompanyUser, type CustomerType } from "@/lib/types";
import { useCustomerStatusLabel, useCustomerTypeLabel, useLeadChannelLabel } from "@/lib/i18n/hooks";

export default function NewCustomerPage() {
  const router = useRouter();
  const t = useTranslations("customerNew");
  const tCommon = useTranslations("common");
  const channelLabel = useLeadChannelLabel();
  const statusLabel = useCustomerStatusLabel();
  const typeLabel = useCustomerTypeLabel();
  const toast = useToast();

  const [name, setName] = useState("");
  const [type, setType] = useState<CustomerType>(CUSTOMER_TYPES[0]);
  const [phone, setPhone] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [instagram, setInstagram] = useState("");
  const [facebook, setFacebook] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [leadSource, setLeadSource] = useState("");
  const [campaign, setCampaign] = useState("");
  const [status, setStatus] = useState<string>(CUSTOMER_STATUSES[0]);
  const [assignedManagerId, setAssignedManagerId] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [users, setUsers] = useState<CompanyUser[]>([]);

  useEffect(() => {
    listCompanyUsers().then(setUsers).catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const customer = await createCustomer({
        name,
        type,
        phone: phone || undefined,
        whatsapp: whatsapp || undefined,
        instagram: instagram || undefined,
        facebook: facebook || undefined,
        email: email || undefined,
        address: address || undefined,
        company_name: companyName || undefined,
        lead_source: leadSource || undefined,
        advertising_campaign: campaign || undefined,
        status: status as (typeof CUSTOMER_STATUSES)[number],
        assigned_manager_id: assignedManagerId || undefined,
        notes: notes || undefined,
      });
      toast.success(t("customerCreated"));
      router.push(`/crm/customers/${customer.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Card>
        <CardHeader title={t("title")} subtitle={t("subtitle")} />
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <TextField label={t("name")} value={name} onChange={(e) => setName(e.target.value)} required autoFocus />

          <SelectField label={t("type")} value={type} onChange={(e) => setType(e.target.value as CustomerType)}>
            {CUSTOMER_TYPES.map((ct) => (
              <option key={ct} value={ct}>
                {typeLabel(ct)}
              </option>
            ))}
          </SelectField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField label={t("phone")} value={phone} onChange={(e) => setPhone(e.target.value)} />
            <TextField label={t("whatsapp")} value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} />
            <TextField label={t("instagram")} value={instagram} onChange={(e) => setInstagram(e.target.value)} />
            <TextField label={t("facebook")} value={facebook} onChange={(e) => setFacebook(e.target.value)} />
            <TextField label={t("email")} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextField label={t("companyName")} value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
          </div>

          <TextField label={t("address")} value={address} onChange={(e) => setAddress(e.target.value)} />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectField label={t("leadSource")} value={leadSource} onChange={(e) => setLeadSource(e.target.value)}>
              <option value="">{t("leadSourceNone")}</option>
              {LEAD_SOURCE_CHANNELS.map((channel) => (
                <option key={channel} value={channel}>
                  {channelLabel(channel)}
                </option>
              ))}
            </SelectField>
            <SelectField label={t("status")} value={status} onChange={(e) => setStatus(e.target.value)}>
              {CUSTOMER_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </SelectField>
            <SelectField
              label={t("assignedManager")}
              value={assignedManagerId}
              onChange={(e) => setAssignedManagerId(e.target.value)}
            >
              <option value="">{t("unassigned")}</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name}
                </option>
              ))}
            </SelectField>
          </div>

          <TextField label={t("advertisingCampaign")} value={campaign} onChange={(e) => setCampaign(e.target.value)} />

          <TextAreaField label={t("notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => router.back()}>
              {tCommon("cancel")}
            </Button>
            <Button type="submit" loading={submitting}>
              {t("title")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
