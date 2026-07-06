"""Domain events published by the Communication Center module."""

CHANNEL_CREATED = "ChannelCreated"
CONVERSATION_CREATED = "ConversationCreated"
CONVERSATION_ASSIGNED = "ConversationAssigned"
CONVERSATION_STATUS_CHANGED = "ConversationStatusChanged"
CONVERSATION_LINKED = "ConversationLinked"
CONVERSATION_NOTE_ADDED = "ConversationNoteAdded"
MESSAGE_RECEIVED = "MessageReceived"
MESSAGE_SENT = "MessageSent"
MESSAGE_TEMPLATE_CREATED = "MessageTemplateCreated"

# Version 2.9 -- Real Integrations
CHANNEL_CREDENTIAL_CONFIGURED = "ChannelCredentialConfigured"
CHANNEL_HEALTH_CHECKED = "ChannelHealthChecked"
MESSAGE_QUEUED_FOR_RETRY = "MessageQueuedForRetry"
MESSAGE_DELIVERY_STATUS_UPDATED = "MessageDeliveryStatusUpdated"
IMAP_MAILBOX_SYNCED = "ImapMailboxSynced"
PROVIDER_WEBHOOK_RECEIVED = "ProviderWebhookReceived"
