"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { createCustomer } from "@/lib/api/crm";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextField } from "@/components/ui/field";
import { LEAD_SOURCE_CHANNELS } from "@/lib/types";
import { useLeadChannelLabel } from "@/lib/i18n/hooks";

export default function NewCustomerPage() {
  const router = useRouter();
  const t = useTranslations("customerNew");
  const tCommon = useTranslations("common");
  const tCustomerType = useTranslations("customerType");
  const channelLabel = useLeadChannelLabel();
  const [name, setName] = useState("");
  const [type, setType] = useState<"individual" | "business">("business");
  const [leadSource, setLeadSource] = useState("");
  const [campaign, setCampaign] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const customer = await createCustomer({
        name,
        type,
        lead_source: leadSource || undefined,
        advertising_campaign: campaign || undefined,
        contact: contactName
          ? { full_name: contactName, email: contactEmail || undefined, phone: contactPhone || undefined }
          : undefined,
      });
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
        <CardHeader title={t("title")} />
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <TextField label={t("name")} value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          <SelectField label={t("type")} value={type} onChange={(e) => setType(e.target.value as "individual" | "business")}>
            <option value="business">{tCustomerType("business")}</option>
            <option value="individual">{tCustomerType("individual")}</option>
          </SelectField>
          <SelectField label={t("leadSource")} value={leadSource} onChange={(e) => setLeadSource(e.target.value)}>
            <option value="">{t("leadSourceNone")}</option>
            {LEAD_SOURCE_CHANNELS.map((channel) => (
              <option key={channel} value={channel}>
                {channelLabel(channel)}
              </option>
            ))}
          </SelectField>
          <TextField label={t("advertisingCampaign")} value={campaign} onChange={(e) => setCampaign(e.target.value)} />

          <div className="border-t border-border pt-4">
            <p className="mb-3 text-sm font-medium text-text-primary">{t("primaryContact")}</p>
            <div className="flex flex-col gap-4">
              <TextField label={t("contactFullName")} value={contactName} onChange={(e) => setContactName(e.target.value)} />
              <TextField
                label={t("contactEmail")}
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
              <TextField label={t("contactPhone")} value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
            </div>
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => router.back()}>
              {tCommon("cancel")}
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? t("creating") : t("title")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
