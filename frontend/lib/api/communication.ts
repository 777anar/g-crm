import { apiRequest } from "../api-client";
import type {
  Channel,
  Conversation,
  ConversationNote,
  Message,
  MessageAttachment,
  MessageTemplate,
  Paginated,
} from "../types";

const BASE = "/api/v1/communication";

// ── Channels ──────────────────────────────────────────────────────────────────

export function listChannels(params: { channelType?: string; includeInactive?: boolean } = {}) {
  return apiRequest<{ items: Channel[] }>(`${BASE}/channels`, {
    searchParams: { channel_type: params.channelType, include_inactive: params.includeInactive },
  });
}

export function createChannel(input: { channel_type: string; display_name: string; identifier?: string }) {
  return apiRequest<Channel>(`${BASE}/channels`, { method: "POST", body: input });
}

export function updateChannel(
  id: string,
  input: { display_name?: string; identifier?: string; is_active?: boolean }
) {
  return apiRequest<Channel>(`${BASE}/channels/${id}`, { method: "PATCH", body: input });
}

// ── Conversations ─────────────────────────────────────────────────────────────

export function listConversations(
  params: {
    channelId?: string;
    status?: string;
    assignedTo?: string;
    customerId?: string;
    leadId?: string;
    search?: string;
    sort?: string;
    limit?: number;
    cursor?: string;
  } = {}
) {
  return apiRequest<Paginated<Conversation>>(`${BASE}/conversations`, {
    searchParams: {
      channel_id: params.channelId,
      status: params.status,
      assigned_to: params.assignedTo,
      customer_id: params.customerId,
      lead_id: params.leadId,
      search: params.search || undefined,
      sort: params.sort,
      limit: params.limit,
      cursor: params.cursor,
    },
  });
}

export function startConversation(input: {
  channel_id: string;
  external_contact_id: string;
  external_contact_name?: string;
}) {
  return apiRequest<Conversation>(`${BASE}/conversations`, { method: "POST", body: input });
}

export function getConversation(id: string) {
  return apiRequest<Conversation>(`${BASE}/conversations/${id}`);
}

export function updateConversation(
  id: string,
  input: {
    status?: string;
    assigned_to?: string;
    tags?: string[];
    customer_id?: string;
    lead_id?: string;
    project_id?: string;
    quote_id?: string;
    order_id?: string;
  }
) {
  return apiRequest<Conversation>(`${BASE}/conversations/${id}`, { method: "PATCH", body: input });
}

export function markConversationRead(id: string) {
  return apiRequest<Conversation>(`${BASE}/conversations/${id}/read`, { method: "POST" });
}

// ── Messages ──────────────────────────────────────────────────────────────────

export function listMessages(conversationId: string, limit = 100) {
  return apiRequest<{ items: Message[] }>(`${BASE}/conversations/${conversationId}/messages`, {
    searchParams: { limit },
  });
}

export function sendMessage(
  conversationId: string,
  input: { body: string; message_type?: string; template_id?: string }
) {
  return apiRequest<Message>(`${BASE}/conversations/${conversationId}/messages`, { method: "POST", body: input });
}

export function receiveInboundMessage(input: {
  channel_id: string;
  external_contact_id: string;
  external_contact_name?: string;
  body: string;
  message_type?: string;
}) {
  return apiRequest<Message>(`${BASE}/inbound`, { method: "POST", body: input });
}

export function listMessageAttachments(conversationId: string, messageId: string) {
  return apiRequest<{ items: MessageAttachment[] }>(
    `${BASE}/conversations/${conversationId}/messages/${messageId}/attachments`
  );
}

export function addMessageAttachment(
  conversationId: string,
  messageId: string,
  input: { document_id: string; file_name?: string }
) {
  return apiRequest<MessageAttachment>(
    `${BASE}/conversations/${conversationId}/messages/${messageId}/attachments`,
    { method: "POST", body: input }
  );
}

export function uploadCommunicationAttachment(messageId: string, file: File) {
  const formData = new FormData();
  formData.append("module", "communication");
  formData.append("related_entity_type", "message");
  formData.append("related_entity_id", messageId);
  formData.append("file", file);
  return apiRequest<{ id: string; storage_path: string; mime_type: string }>("/api/v1/core/documents", {
    method: "POST",
    formData,
  });
}

// ── Notes ─────────────────────────────────────────────────────────────────────

export function listConversationNotes(conversationId: string) {
  return apiRequest<{ items: ConversationNote[] }>(`${BASE}/conversations/${conversationId}/notes`);
}

export function addConversationNote(conversationId: string, body: string) {
  return apiRequest<ConversationNote>(`${BASE}/conversations/${conversationId}/notes`, {
    method: "POST",
    body: { body },
  });
}

// ── Templates & quick replies ─────────────────────────────────────────────────

export function listTemplates(params: { channelType?: string; includeInactive?: boolean } = {}) {
  return apiRequest<{ items: MessageTemplate[] }>(`${BASE}/templates`, {
    searchParams: { channel_type: params.channelType, include_inactive: params.includeInactive },
  });
}

export function createTemplate(input: { name: string; body: string; channel_type?: string; shortcut?: string }) {
  return apiRequest<MessageTemplate>(`${BASE}/templates`, { method: "POST", body: input });
}

export function updateTemplate(
  id: string,
  input: { name?: string; body?: string; channel_type?: string; shortcut?: string; is_active?: boolean }
) {
  return apiRequest<MessageTemplate>(`${BASE}/templates/${id}`, { method: "PATCH", body: input });
}
