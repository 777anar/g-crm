"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { convertLead, createLead, listLeads } from "@/lib/api/crm";
import { LEAD_SOURCE_CHANNELS, type Lead } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { LeadStatusBadge, Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SelectField, TextField } from "@/components/ui/field";

const CHANNEL_LABELS: Record<string, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  messenger: "Messenger",
  whatsapp: "WhatsApp",
  manual: "Manual",
};

export default function LeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [channelFilter, setChannelFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [convertingId, setConvertingId] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [sourceChannel, setSourceChannel] = useState<string>("manual");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [campaign, setCampaign] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function reload() {
    try {
      const res = await listLeads({ sourceChannel: channelFilter || undefined });
      setLeads(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to load leads.");
    }
  }

  useEffect(() => {
    setLeads(null);
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelFilter]);

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
      setError(err instanceof ApiRequestError ? err.message : "Failed to create lead.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConvert(leadId: string) {
    setConvertingId(leadId);
    setError(null);
    try {
      const result = await convertLead(leadId);
      router.push(`/crm/customers/${result.customer_id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to convert lead.");
    } finally {
      setConvertingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-text-primary">Leads</h1>

      <Card>
        <CardHeader title="Capture a Lead" />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
          <TextField label="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          <SelectField label="Source Channel" value={sourceChannel} onChange={(e) => setSourceChannel(e.target.value)}>
            {LEAD_SOURCE_CHANNELS.map((channel) => (
              <option key={channel} value={channel}>
                {CHANNEL_LABELS[channel]}
              </option>
            ))}
          </SelectField>
          <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <TextField label="Campaign" value={campaign} onChange={(e) => setCampaign(e.target.value)} />
          <div className="flex items-end">
            <Button type="submit" disabled={submitting || !fullName}>
              {submitting ? "Creating..." : "Create Lead"}
            </Button>
          </div>
        </form>
      </Card>

      <div className="flex items-center gap-2">
        <span className="text-sm text-text-secondary">Filter by channel:</span>
        <button
          className={`rounded-full border px-2 py-0.5 text-xs ${channelFilter === "" ? "border-primary text-primary" : "border-border text-text-secondary"}`}
          onClick={() => setChannelFilter("")}
        >
          All
        </button>
        {LEAD_SOURCE_CHANNELS.map((channel) => (
          <button
            key={channel}
            className={`rounded-full border px-2 py-0.5 text-xs ${channelFilter === channel ? "border-primary text-primary" : "border-border text-text-secondary"}`}
            onClick={() => setChannelFilter(channel)}
          >
            {CHANNEL_LABELS[channel]}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {leads === null && !error && <p className="text-text-secondary">Loading leads...</p>}

      {leads && leads.length === 0 && <EmptyState title="No leads yet" description="Capture your first lead above." />}

      {leads && leads.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-bg text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Channel</th>
                <th className="px-4 py-2 font-medium">Campaign</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id} className="border-b border-border last:border-0 hover:bg-bg">
                  <td className="px-4 py-2 font-medium text-text-primary">{lead.full_name}</td>
                  <td className="px-4 py-2">
                    <Badge tone="info">{CHANNEL_LABELS[lead.source_channel]}</Badge>
                  </td>
                  <td className="px-4 py-2 text-text-secondary">{lead.campaign ?? "—"}</td>
                  <td className="px-4 py-2">
                    <LeadStatusBadge status={lead.status} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    {lead.status !== "converted" && (
                      <Button
                        variant="secondary"
                        onClick={() => handleConvert(lead.id)}
                        disabled={convertingId === lead.id}
                      >
                        {convertingId === lead.id ? "Converting..." : "Convert to Customer"}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
