"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { createCampaign, listCampaigns } from "@/lib/api/marketing";
import { CAMPAIGN_CHANNELS, type Campaign, type CampaignChannel } from "@/lib/types";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { CampaignStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SelectField, TextField } from "@/components/ui/field";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListShortcuts } from "@/lib/use-list-shortcuts";
import { useLeadChannelLabel } from "@/lib/i18n/hooks";
import { formatDate } from "@/lib/format";
import { usePermission } from "@/lib/permissions";

const CREATE_FORM_NAME_INPUT_ID = "campaign-create-name";

export default function CampaignsPage() {
  const t = useTranslations("marketing");
  const tCommon = useTranslations("common");
  const channelLabel = useLeadChannelLabel();
  const canWrite = usePermission("marketing:campaigns:write");
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const search = useDebouncedValue(searchInput, 250);

  const [name, setName] = useState("");
  const [channel, setChannel] = useState<CampaignChannel>(CAMPAIGN_CHANNELS[0]);
  const [budget, setBudget] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(
    async (options: { append?: boolean; cursor?: string } = {}) => {
      try {
        const res = await listCampaigns({ search, cursor: options.cursor });
        setCampaigns((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
        setNextCursor(res.next_cursor);
      } catch (err) {
        setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
      }
    },
    [search, t]
  );

  useEffect(() => {
    setCampaigns(null);
    reload();
  }, [reload]);

  useListShortcuts({
    searchInputRef,
    onCreate: () => document.getElementById(CREATE_FORM_NAME_INPUT_ID)?.focus(),
  });

  function handleLoadMore() {
    if (!nextCursor) return;
    reload({ append: true, cursor: nextCursor });
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createCampaign({
        name,
        channel,
        budget: budget || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setName("");
      setBudget("");
      setStartDate("");
      setEndDate("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("createFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      {canWrite && (
      <Card>
        <CardHeader title={t("createCampaign")} />
        <form className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5" onSubmit={handleCreate}>
          <TextField
            id={CREATE_FORM_NAME_INPUT_ID}
            label={t("name")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <SelectField label={t("channel")} value={channel} onChange={(e) => setChannel(e.target.value as CampaignChannel)}>
            {CAMPAIGN_CHANNELS.map((c) => (
              <option key={c} value={c}>
                {channelLabel(c)}
              </option>
            ))}
          </SelectField>
          <TextField label={t("budget")} type="number" min="0" step="0.01" value={budget} onChange={(e) => setBudget(e.target.value)} />
          <TextField label={t("startDate")} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          <TextField label={t("endDate")} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          <div className="flex items-end lg:col-span-5">
            <Button type="submit" disabled={submitting || !name}>
              {submitting ? t("creating") : t("createCampaign")}
            </Button>
          </div>
        </form>
      </Card>
      )}

      <input
        ref={searchInputRef}
        type="search"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder={t("searchPlaceholder")}
        className="w-full max-w-xs rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
      />

      {error && <p className="text-sm text-danger">{error}</p>}

      {campaigns === null && !error && <TableSkeleton rows={4} columns={5} />}

      {campaigns && campaigns.length === 0 && (
        <EmptyState title={t("noCampaignsYet")} description={t("noCampaignsDesc")} />
      )}

      {campaigns && campaigns.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("name")}</th>
                  <th className="px-4 py-2 font-medium">{t("channel")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-4 py-2 font-medium">{t("budget")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableCreated")}</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => (
                  <tr key={campaign.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-medium text-text-primary">
                      <Link href={`/marketing/campaigns/${campaign.id}`} className="hover:text-primary hover:underline">
                        {campaign.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{channelLabel(campaign.channel)}</td>
                    <td className="px-4 py-2">
                      <CampaignStatusBadge status={campaign.status} />
                    </td>
                    <td className="px-4 py-2 text-text-secondary">
                      {campaign.budget ? `${campaign.currency} ${parseFloat(campaign.budget).toFixed(2)}` : tCommon("dash")}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{formatDate(campaign.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={handleLoadMore}>
                {tCommon("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
