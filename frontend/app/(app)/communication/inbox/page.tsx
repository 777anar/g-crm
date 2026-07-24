"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  addConversationNote,
  getConversation,
  listChannels,
  listConversationNotes,
  listConversations,
  listMessages,
  listTemplates,
  markConversationRead,
  sendMessage,
  startConversation,
  updateConversation,
} from "@/lib/api/communication";
import { listCompanyUsers } from "@/lib/api/companies";
import { analyzeConversation, draftConversationReply } from "@/lib/api/ai";
import {
  CONVERSATION_STATUSES,
  type AIRecommendation,
  type Channel,
  type CompanyUser,
  type Conversation,
  type ConversationNote,
  type Message,
  type MessageTemplate,
  type SuggestedReplyResponse,
} from "@/lib/types";
import { ChannelTypeBadge, ConversationStatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { RecommendationCard } from "@/components/recommendation-card";
import { formatDateTime } from "@/lib/format";
import { ApiRequestError } from "@/lib/api-client";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { usePermission } from "@/lib/permissions";

type MobilePane = "list" | "chat" | "profile";

export default function InboxPage() {
  const t = useTranslations("communication");
  const tCommon = useTranslations("common");
  const canWrite = usePermission("communication:conversations:write");

  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);

  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput, 250);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[] | null>(null);
  const [notes, setNotes] = useState<ConversationNote[] | null>(null);
  const [composerText, setComposerText] = useState("");
  const [noteText, setNoteText] = useState("");
  const [sending, setSending] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [mobilePane, setMobilePane] = useState<MobilePane>("list");
  const [showNewConversation, setShowNewConversation] = useState(false);
  const [newConvForm, setNewConvForm] = useState({ channel_id: "", external_contact_id: "", external_contact_name: "" });
  const [startingConversation, setStartingConversation] = useState(false);
  const tAi = useTranslations("ai");
  const [analyzingConversation, setAnalyzingConversation] = useState(false);
  const [draftingReply, setDraftingReply] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);
  const [conversationRecs, setConversationRecs] = useState<Record<string, AIRecommendation[]>>({});

  const loadConversations = useCallback(() => {
    listConversations({
      status: statusFilter || undefined,
      channelId: channelFilter || undefined,
      search: search || undefined,
      limit: 100,
    })
      .then((r) => setConversations(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [statusFilter, channelFilter, search, t]);

  useEffect(() => {
    setConversations(null);
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    listChannels().then((r) => setChannels(r.items)).catch(() => {});
    listCompanyUsers().then(setUsers).catch(() => {});
    listTemplates().then((r) => setTemplates(r.items)).catch(() => {});
  }, []);

  const loadConversationDetail = useCallback(async (id: string) => {
    setMessages(null);
    setNotes(null);
    const [conv, messageRes, noteRes] = await Promise.all([
      getConversation(id),
      listMessages(id),
      listConversationNotes(id),
    ]);
    setSelected(conv);
    setMessages(messageRes.items);
    setNotes(noteRes.items);
    if (conv.unread_count > 0) {
      await markConversationRead(id);
      loadConversations();
    }
  }, [loadConversations]);

  function handleSelectConversation(id: string) {
    setSelectedId(id);
    setMobilePane("chat");
    loadConversationDetail(id);
  }

  async function handleStartConversation(e: React.FormEvent) {
    e.preventDefault();
    if (!newConvForm.channel_id || !newConvForm.external_contact_id.trim()) return;
    setStartingConversation(true);
    try {
      const conv = await startConversation({
        channel_id: newConvForm.channel_id,
        external_contact_id: newConvForm.external_contact_id.trim(),
        external_contact_name: newConvForm.external_contact_name || undefined,
      });
      setNewConvForm({ channel_id: "", external_contact_id: "", external_contact_name: "" });
      setShowNewConversation(false);
      loadConversations();
      handleSelectConversation(conv.id);
    } finally {
      setStartingConversation(false);
    }
  }

  async function handleSend() {
    if (!selectedId || !composerText.trim()) return;
    setSending(true);
    try {
      await sendMessage(selectedId, { body: composerText.trim() });
      setComposerText("");
      await loadConversationDetail(selectedId);
      loadConversations();
    } finally {
      setSending(false);
    }
  }

  async function handleAnalyzeConversation() {
    if (!selectedId) return;
    setAnalyzingConversation(true);
    try {
      const result = await analyzeConversation(selectedId);
      setConversationRecs((prev) => ({ ...prev, [selectedId]: result.items }));
      setShowAiPanel(true);
    } finally {
      setAnalyzingConversation(false);
    }
  }

  async function handleDraftReply() {
    if (!selectedId) return;
    setDraftingReply(true);
    try {
      const result = await draftConversationReply(selectedId);
      setConversationRecs((prev) => ({ ...prev, [selectedId]: [...(prev[selectedId] ?? []), ...result.items] }));
      setShowAiPanel(true);
    } finally {
      setDraftingReply(false);
    }
  }

  function handleConversationRecommendationReviewed(updated: AIRecommendation) {
    if (!selectedId) return;
    setConversationRecs((prev) => ({
      ...prev,
      [selectedId]: (prev[selectedId] ?? []).map((r) => (r.id === updated.id ? updated : r)),
    }));
    // Accepting a suggested_reply never sends anything itself -- it just
    // loads the draft into the compose box so the human can edit and send
    // it through the existing Send action, same as picking a template.
    if (updated.recommendation_type === "suggested_reply" && updated.status === "accepted") {
      const draft = (updated.response as SuggestedReplyResponse).draft_reply;
      if (draft) setComposerText(draft);
    }
  }

  async function handleAddNote() {
    if (!selectedId || !noteText.trim()) return;
    await addConversationNote(selectedId, noteText.trim());
    setNoteText("");
    const noteRes = await listConversationNotes(selectedId);
    setNotes(noteRes.items);
  }

  async function handleUpdate(input: Parameters<typeof updateConversation>[1]) {
    if (!selectedId) return;
    const updated = await updateConversation(selectedId, input);
    setSelected(updated);
    loadConversations();
  }

  const applicableTemplates = useMemo(() => {
    if (!selected) return templates;
    const channel = channels.find((c) => c.id === selected.channel_id);
    if (!channel) return templates;
    return templates.filter((tpl) => !tpl.channel_type || tpl.channel_type === channel.channel_type);
  }, [templates, selected, channels]);

  const channelFor = (channelId: string) => channels.find((c) => c.id === channelId);

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4 lg:flex-row">
      {/* Conversation list */}
      <div className={`flex w-full flex-col gap-3 lg:w-80 lg:shrink-0 ${mobilePane === "list" ? "flex" : "hidden lg:flex"}`}>
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-text-primary">{t("inboxTitle")}</h1>
          {canWrite && (
            <Button variant="secondary" onClick={() => setShowNewConversation((v) => !v)}>
              {t("newConversation")}
            </Button>
          )}
        </div>

        {canWrite && showNewConversation && (
          <form onSubmit={handleStartConversation} className="flex flex-col gap-2 rounded-md border border-border p-2">
            <select
              value={newConvForm.channel_id}
              onChange={(e) => setNewConvForm({ ...newConvForm, channel_id: e.target.value })}
              className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
              required
            >
              <option value="">{t("selectChannel")}</option>
              {channels.map((c) => (
                <option key={c.id} value={c.id}>{c.display_name}</option>
              ))}
            </select>
            <input
              value={newConvForm.external_contact_id}
              onChange={(e) => setNewConvForm({ ...newConvForm, external_contact_id: e.target.value })}
              placeholder={t("contactIdPlaceholder")}
              className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
              required
            />
            <input
              value={newConvForm.external_contact_name}
              onChange={(e) => setNewConvForm({ ...newConvForm, external_contact_name: e.target.value })}
              placeholder={t("contactNamePlaceholder")}
              className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
            />
            <Button type="submit" disabled={startingConversation}>
              {startingConversation ? t("saving") : t("startConversation")}
            </Button>
          </form>
        )}

        <div className="flex flex-col gap-2">
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={tCommon("search")}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
          />
          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="flex-1 rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
            >
              <option value="">{tCommon("allStatuses")}</option>
              {CONVERSATION_STATUSES.map((s) => (
                <option key={s} value={s}>{t(s as Parameters<typeof t>[0])}</option>
              ))}
            </select>
            <select
              value={channelFilter}
              onChange={(e) => setChannelFilter(e.target.value)}
              className="flex-1 rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
            >
              <option value="">{t("allChannels")}</option>
              {channels.map((c) => (
                <option key={c.id} value={c.id}>{c.display_name}</option>
              ))}
            </select>
          </div>
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}
        {conversations === null && !error && <TableSkeleton rows={5} columns={1} />}
        {conversations && conversations.length === 0 && (
          <EmptyState title={t("noConversationsYet")} description={t("noConversationsDesc")} />
        )}

        <div className="flex-1 overflow-y-auto rounded-lg border border-border bg-surface">
          {conversations?.map((conv) => {
            const channel = channelFor(conv.channel_id);
            return (
              <button
                key={conv.id}
                onClick={() => handleSelectConversation(conv.id)}
                className={`flex w-full flex-col gap-1 border-b border-border p-3 text-left last:border-0 hover:bg-bg ${selectedId === conv.id ? "bg-bg" : ""}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium text-text-primary">
                    {conv.external_contact_name || conv.external_contact_id}
                  </span>
                  {conv.unread_count > 0 && (
                    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-xs font-semibold text-white">
                      {conv.unread_count}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {channel && <ChannelTypeBadge channelType={channel.channel_type} />}
                  <ConversationStatusBadge status={conv.status} />
                </div>
                <p className="truncate text-xs text-text-secondary">
                  {conv.last_message_preview || t("noMessagesYet")}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Chat window */}
      <div className={`flex flex-1 flex-col gap-3 rounded-lg border border-border bg-surface p-3 ${mobilePane === "chat" ? "flex" : "hidden lg:flex"}`}>
        {!selected ? (
          <EmptyState title={t("selectConversation")} />
        ) : (
          <>
            <div className="flex items-center justify-between border-b border-border pb-2">
              <div className="flex items-center gap-2">
                <button className="text-sm text-primary hover:underline lg:hidden" onClick={() => setMobilePane("list")}>
                  ← {tCommon("back")}
                </button>
                <span className="font-medium text-text-primary">
                  {selected.external_contact_name || selected.external_contact_id}
                </span>
                <ConversationStatusBadge status={selected.status} />
              </div>
              <div className="flex items-center gap-2">
                <Button variant="secondary" onClick={handleDraftReply} disabled={draftingReply}>
                  {tAi("draftReply")}
                </Button>
                {conversationRecs[selected.id] ? (
                  <Button variant="secondary" onClick={() => setShowAiPanel((v) => !v)}>
                    {showAiPanel ? tAi("hideDetails") : tAi("showDetails")}
                  </Button>
                ) : (
                  <Button variant="secondary" onClick={handleAnalyzeConversation} disabled={analyzingConversation}>
                    {tAi("runAnalysis")}
                  </Button>
                )}
                <button className="text-sm text-primary hover:underline lg:hidden" onClick={() => setMobilePane("profile")}>
                  {t("profile")} →
                </button>
              </div>
            </div>

            {showAiPanel && conversationRecs[selected.id] && (
              <div className="grid grid-cols-1 gap-2 border-b border-border pb-3 sm:grid-cols-2">
                {conversationRecs[selected.id].map((rec) => (
                  <RecommendationCard key={rec.id} recommendation={rec} onReviewed={handleConversationRecommendationReviewed} />
                ))}
              </div>
            )}

            <div className="flex-1 overflow-y-auto">
              {messages === null && <TableSkeleton rows={3} columns={1} />}
              {messages && messages.length === 0 && <EmptyState title={t("noMessagesYet")} />}
              <div className="flex flex-col gap-2">
                {messages?.map((msg) => (
                  <div
                    key={msg.id}
                    className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                      msg.direction === "outbound"
                        ? "ml-auto bg-primary text-white"
                        : "bg-bg text-text-primary"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.body}</p>
                    <p className={`mt-1 text-xs ${msg.direction === "outbound" ? "text-white/70" : "text-text-secondary"}`}>
                      {formatDateTime(msg.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-2 border-t border-border pt-2">
              {showTemplates && (
                <div className="max-h-40 overflow-y-auto rounded-md border border-border bg-bg p-2">
                  {applicableTemplates.length === 0 && (
                    <p className="text-xs text-text-secondary">{t("noTemplatesYet")}</p>
                  )}
                  {applicableTemplates.map((tpl) => (
                    <button
                      key={tpl.id}
                      onClick={() => {
                        setComposerText(tpl.body);
                        setShowTemplates(false);
                      }}
                      className="block w-full rounded px-2 py-1 text-left text-xs text-text-primary hover:bg-surface"
                    >
                      <span className="font-medium">{tpl.name}</span>
                      {tpl.shortcut && <span className="ml-1 text-text-secondary">/{tpl.shortcut}</span>}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <textarea
                  value={composerText}
                  onChange={(e) => setComposerText(e.target.value)}
                  placeholder={t("typeMessage")}
                  rows={2}
                  className="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
                />
                <div className="flex flex-col gap-2">
                  <Button variant="secondary" onClick={() => setShowTemplates((v) => !v)}>
                    {t("templates")}
                  </Button>
                  {canWrite && (
                    <Button onClick={handleSend} disabled={sending || !composerText.trim()}>
                      {sending ? t("sending") : t("send")}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Customer profile side panel */}
      <div className={`flex w-full flex-col gap-3 rounded-lg border border-border bg-surface p-3 lg:w-72 lg:shrink-0 ${mobilePane === "profile" ? "flex" : "hidden lg:flex"}`}>
        {!selected ? (
          <EmptyState title={t("selectConversation")} />
        ) : (
          <>
            <button className="text-sm text-primary hover:underline lg:hidden" onClick={() => setMobilePane("chat")}>
              ← {tCommon("back")}
            </button>

            <div>
              <h3 className="mb-1 text-sm font-semibold text-text-primary">{t("contact")}</h3>
              {selected.customer_id ? (
                <Link href={`/crm/customers/${selected.customer_id}`} className="text-sm text-primary hover:underline">
                  {t("viewCustomerProfile")} →
                </Link>
              ) : selected.lead_id ? (
                <Link href="/crm/leads" className="text-sm text-primary hover:underline">
                  {t("viewAsLead")} →
                </Link>
              ) : (
                <p className="text-sm text-text-secondary">{t("noCrmLinkYet")}</p>
              )}
            </div>

            <div>
              <label className="text-xs text-text-secondary">{t("status")}</label>
              <select
                value={selected.status}
                onChange={(e) => handleUpdate({ status: e.target.value })}
                disabled={!canWrite}
                className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary"
              >
                {CONVERSATION_STATUSES.map((s) => (
                  <option key={s} value={s}>{t(s as Parameters<typeof t>[0])}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs text-text-secondary">{t("assignee")}</label>
              <select
                value={selected.assigned_to ?? ""}
                onChange={(e) => handleUpdate({ assigned_to: e.target.value || undefined })}
                disabled={!canWrite}
                className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary"
              >
                <option value="">{t("unassigned")}</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs text-text-secondary">{t("tags")}</label>
              <input
                defaultValue={selected.tags.join(", ")}
                onBlur={(e) =>
                  handleUpdate({ tags: e.target.value.split(",").map((tag) => tag.trim()).filter(Boolean) })
                }
                disabled={!canWrite}
                className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary"
              />
            </div>

            <div className="flex-1 overflow-y-auto border-t border-border pt-2">
              <h3 className="mb-1 text-sm font-semibold text-text-primary">{t("internalNotes")}</h3>
              {notes && notes.length === 0 && <p className="text-xs text-text-secondary">{t("noNotesYet")}</p>}
              <ul className="flex flex-col gap-2">
                {notes?.map((note) => (
                  <li key={note.id} className="rounded-md bg-bg p-2 text-xs text-text-primary">
                    <p>{note.body}</p>
                    <p className="mt-1 text-text-secondary">{formatDateTime(note.created_at)}</p>
                  </li>
                ))}
              </ul>
              {canWrite && (
                <div className="mt-2 flex gap-2">
                  <input
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder={t("addNote")}
                    className="flex-1 rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
                  />
                  <Button variant="secondary" onClick={handleAddNote} disabled={!noteText.trim()}>
                    {tCommon("save")}
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
