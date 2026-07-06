"use client";

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { convertLead, createLead, listLeads } from "@/lib/api/crm";
import { analyzeLead } from "@/lib/api/ai";
import { LEAD_SOURCE_CHANNELS, type AIRecommendation, type Lead } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { LeadStatusBadge, Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SelectField, TextField } from "@/components/ui/field";
import { SortableHeader } from "@/components/ui/sortable-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { RecommendationCard } from "@/components/recommendation-card";
import { formatDate } from "@/lib/format";
import { useLeadChannelLabel } from "@/lib/i18n/hooks";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";

const CAPTURE_FORM_NAME_INPUT_ID = "lead-capture-full-name";

export default function LeadsPage() {
  const router = useRouter();
  const t = useTranslations("leads");
  const tCommon = useTranslations("common");
  const channelLabel = useLeadChannelLabel();
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [channelFilter, setChannelFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [error, setError] = useState<string | null>(null);
  const [convertingId, setConvertingId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);
  const tAi = useTranslations("ai");

  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [expandedLeadId, setExpandedLeadId] = useState<string | null>(null);
  const [recsByLead, setRecsByLead] = useState<Record<string, AIRecommendation[]>>({});

  const [fullName, setFullName] = useState("");
  const [sourceChannel, setSourceChannel] = useState<string>(LEAD_SOURCE_CHANNELS[0]);
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [campaign, setCampaign] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(async () => {
    try {
      const res = await listLeads({ sourceChannel: channelFilter || undefined, search, sort });
      setLeads(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }, [channelFilter, search, sort, t]);

  useEffect(() => {
    setLeads(null);
    reload();
  }, [reload]);

  useListShortcuts({
    searchInputRef,
    onCreate: () => document.getElementById(CAPTURE_FORM_NAME_INPUT_ID)?.focus(),
  });

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createLead({
        full_name: fullName,
        source_channel: sourceChannel,
        email: email || undefined,
        phone: phone || undefined,
        campaign: campaign || undefined,
      });
      setFullName("");
      setEmail("");
      setPhone("");
      setCampaign("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAnalyze(leadId: string) {
    setAnalyzingId(leadId);
    setError(null);
    try {
      const result = await analyzeLead(leadId);
      setRecsByLead((prev) => ({ ...prev, [leadId]: result.items }));
      setExpandedLeadId(leadId);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : tAi("loadFailed"));
    } finally {
      setAnalyzingId(null);
    }
  }

  function handleRecommendationReviewed(leadId: string, updated: AIRecommendation) {
    setRecsByLead((prev) => ({
      ...prev,
      [leadId]: (prev[leadId] ?? []).map((r) => (r.id === updated.id ? updated : r)),
    }));
  }

  async function handleConvert(leadId: string) {
    setConvertingId(leadId);
    setError(null);
    try {
      const result = await convertLead(leadId);
      router.push(`/crm/customers/${result.customer_id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("convertFailed"));
    } finally {
      setConvertingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("captureLead")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
          <TextField
            id={CAPTURE_FORM_NAME_INPUT_ID}
            label={t("fullName")}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
          <SelectField label={t("sourceChannel")} value={sourceChannel} onChange={(e) => setSourceChannel(e.target.value)}>
            {LEAD_SOURCE_CHANNELS.map((channel) => (
              <option key={channel} value={channel}>
                {channelLabel(channel)}
              </option>
            ))}
          </SelectField>
          <TextField label={t("email")} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField label={t("phone")} value={phone} onChange={(e) => setPhone(e.target.value)} />
          <TextField label={t("campaign")} value={campaign} onChange={(e) => setCampaign(e.target.value)} />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !fullName}>
              {submitting ? t("creating") : t("createLead")}
            </Button>
          </div>
        </form>
      </Card>

      <input
        ref={searchInputRef}
        type="search"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder={t("searchPlaceholder")}
        className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
      />

      <div className="flex items-center gap-2">
        <span className="text-sm text-text-secondary">{t("filterByChannel")}</span>
        <button
          className={`rounded-full border px-2 py-0.5 text-xs ${channelFilter === "" ? "border-primary text-primary" : "border-border text-text-secondary"}`}
          onClick={() => setChannelFilter("")}
        >
          {t("all")}
        </button>
        {LEAD_SOURCE_CHANNELS.map((channel) => (
          <button
            key={channel}
            className={`rounded-full border px-2 py-0.5 text-xs ${channelFilter === channel ? "border-primary text-primary" : "border-border text-text-secondary"}`}
            onClick={() => setChannelFilter(channel)}
          >
            {channelLabel(channel)}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {leads === null && !error && <TableSkeleton rows={4} columns={5} />}

      {leads && leads.length === 0 && <EmptyState title={t("noLeadsYet")} description={t("noLeadsDesc")} />}

      {leads && leads.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <SortableHeader field="full_name" label={t("tableName")} sort={sort} onSortChange={setSort} />
                <th className="px-4 py-2 font-medium">{t("tableChannel")}</th>
                <th className="px-4 py-2 font-medium">{t("tableCampaign")}</th>
                <SortableHeader field="status" label={t("tableStatus")} sort={sort} onSortChange={setSort} />
                <SortableHeader field="created_at" label={t("tableCaptured")} sort={sort} onSortChange={setSort} />
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <Fragment key={lead.id}>
                  <tr className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-medium text-text-primary">{lead.full_name}</td>
                    <td className="px-4 py-2">
                      <Badge tone="info">{channelLabel(lead.source_channel)}</Badge>
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{lead.campaign ?? tCommon("dash")}</td>
                    <td className="px-4 py-2">
                      <LeadStatusBadge status={lead.status} />
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{formatDate(lead.created_at)}</td>
                    <td className="px-4 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        {recsByLead[lead.id] ? (
                          <Button
                            variant="secondary"
                            onClick={() => setExpandedLeadId(expandedLeadId === lead.id ? null : lead.id)}
                          >
                            {expandedLeadId === lead.id ? tAi("hideDetails") : tAi("showDetails")}
                          </Button>
                        ) : (
                          <Button
                            variant="secondary"
                            onClick={() => handleAnalyze(lead.id)}
                            disabled={analyzingId === lead.id}
                          >
                            {analyzingId === lead.id ? tAi("runAnalysis") : tAi("analyzeLead")}
                          </Button>
                        )}
                        {lead.status !== "converted" && (
                          <Button
                            variant="secondary"
                            onClick={() => handleConvert(lead.id)}
                            disabled={convertingId === lead.id}
                          >
                            {convertingId === lead.id ? t("converting") : t("convertToCustomer")}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expandedLeadId === lead.id && recsByLead[lead.id] && (
                    <tr key={`${lead.id}-ai`} className="border-b border-border bg-bg">
                      <td colSpan={6} className="px-4 py-3">
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                          {recsByLead[lead.id].map((rec) => (
                            <RecommendationCard
                              key={rec.id}
                              recommendation={rec}
                              onReviewed={(updated) => handleRecommendationReviewed(lead.id, updated)}
                            />
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
