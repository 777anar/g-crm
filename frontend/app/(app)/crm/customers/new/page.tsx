"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCustomer } from "@/lib/api/crm";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { SelectField, TextField } from "@/components/ui/field";

export default function NewCustomerPage() {
  const router = useRouter();
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
      setError(err instanceof ApiRequestError ? err.message : "Failed to create customer.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Card>
        <CardHeader title="Create Customer" />
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          <SelectField label="Type" value={type} onChange={(e) => setType(e.target.value as "individual" | "business")}>
            <option value="business">Business</option>
            <option value="individual">Individual</option>
          </SelectField>
          <SelectField label="Lead Source" value={leadSource} onChange={(e) => setLeadSource(e.target.value)}>
            <option value="">None</option>
            <option value="instagram">Instagram</option>
            <option value="facebook">Facebook</option>
            <option value="messenger">Messenger</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="manual">Manual</option>
          </SelectField>
          <TextField label="Advertising Campaign" value={campaign} onChange={(e) => setCampaign(e.target.value)} />

          <div className="border-t border-border pt-4">
            <p className="mb-3 text-sm font-medium text-text-primary">Primary Contact (optional)</p>
            <div className="flex flex-col gap-4">
              <TextField label="Contact Full Name" value={contactName} onChange={(e) => setContactName(e.target.value)} />
              <TextField
                label="Contact Email"
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
              <TextField label="Contact Phone" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
            </div>
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Customer"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
