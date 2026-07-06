"""Pure value objects for the Communication Center module. No framework or
DB imports."""

# ── Channels ─────────────────────────────────────────────────────────────────

CHANNEL_TYPE_WHATSAPP = "whatsapp"
CHANNEL_TYPE_INSTAGRAM = "instagram"
CHANNEL_TYPE_MESSENGER = "messenger"
CHANNEL_TYPE_EMAIL = "email"
CHANNEL_TYPE_SMS = "sms"
CHANNEL_TYPE_WEBHOOK = "webhook"
VALID_CHANNEL_TYPES = {
    CHANNEL_TYPE_WHATSAPP,
    CHANNEL_TYPE_INSTAGRAM,
    CHANNEL_TYPE_MESSENGER,
    CHANNEL_TYPE_EMAIL,
    CHANNEL_TYPE_SMS,
    CHANNEL_TYPE_WEBHOOK,
}

# ── Real integration providers (Version 2.9) ────────────────────────────────
#
# `NullChannelProvider` remains the default for every channel type (see
# infrastructure/providers/registry.py) -- a channel only gets a real
# provider once a company explicitly configures credentials for it via
# ChannelCredential. This is what keeps every existing Communication Center
# behavior (and every pre-2.9 test) unchanged: no credential row means no
# behavior change at all.

PROVIDER_NULL = "null"
PROVIDER_META_WHATSAPP = "meta_whatsapp"
PROVIDER_META_INSTAGRAM = "meta_instagram"
PROVIDER_META_MESSENGER = "meta_messenger"
PROVIDER_SMTP = "smtp"
PROVIDER_TWILIO_SMS = "twilio_sms"
PROVIDER_WEBHOOK = "webhook"
VALID_PROVIDERS = {
    PROVIDER_NULL,
    PROVIDER_META_WHATSAPP,
    PROVIDER_META_INSTAGRAM,
    PROVIDER_META_MESSENGER,
    PROVIDER_SMTP,
    PROVIDER_TWILIO_SMS,
    PROVIDER_WEBHOOK,
}

# Which real provider(s) a given channel_type may be configured with -- e.g.
# you cannot point a `sms` channel at the `meta_whatsapp` provider. `email`
# maps to `smtp` for sending; IMAP sync is configured on the same credential
# row (see ChannelCredential) since a mailbox needs both to be a channel.
VALID_PROVIDERS_FOR_CHANNEL_TYPE = {
    CHANNEL_TYPE_WHATSAPP: {PROVIDER_META_WHATSAPP},
    CHANNEL_TYPE_INSTAGRAM: {PROVIDER_META_INSTAGRAM},
    CHANNEL_TYPE_MESSENGER: {PROVIDER_META_MESSENGER},
    CHANNEL_TYPE_EMAIL: {PROVIDER_SMTP},
    CHANNEL_TYPE_SMS: {PROVIDER_TWILIO_SMS},
    CHANNEL_TYPE_WEBHOOK: {PROVIDER_WEBHOOK},
}

# ── Health monitoring ────────────────────────────────────────────────────────

HEALTH_STATUS_UNKNOWN = "unknown"
HEALTH_STATUS_OK = "ok"
HEALTH_STATUS_ERROR = "error"
VALID_HEALTH_STATUSES = {HEALTH_STATUS_UNKNOWN, HEALTH_STATUS_OK, HEALTH_STATUS_ERROR}

# ── Retry queue ──────────────────────────────────────────────────────────────

QUEUE_STATUS_PENDING = "pending"
QUEUE_STATUS_PROCESSING = "processing"
QUEUE_STATUS_SENT = "sent"
QUEUE_STATUS_FAILED = "failed"
VALID_QUEUE_STATUSES = {QUEUE_STATUS_PENDING, QUEUE_STATUS_PROCESSING, QUEUE_STATUS_SENT, QUEUE_STATUS_FAILED}
TERMINAL_QUEUE_STATUSES = {QUEUE_STATUS_SENT, QUEUE_STATUS_FAILED}
DEFAULT_MAX_QUEUE_ATTEMPTS = 5

# ── Integration logs ─────────────────────────────────────────────────────────

LOG_DIRECTION_OUTBOUND = "outbound"
LOG_DIRECTION_INBOUND = "inbound"
VALID_LOG_DIRECTIONS = {LOG_DIRECTION_OUTBOUND, LOG_DIRECTION_INBOUND}

# ── Conversations ────────────────────────────────────────────────────────────

CONVERSATION_STATUS_OPEN = "open"
CONVERSATION_STATUS_PENDING = "pending"
CONVERSATION_STATUS_CLOSED = "closed"
VALID_CONVERSATION_STATUSES = {
    CONVERSATION_STATUS_OPEN,
    CONVERSATION_STATUS_PENDING,
    CONVERSATION_STATUS_CLOSED,
}
DEFAULT_CONVERSATION_STATUS = CONVERSATION_STATUS_OPEN

# Unlike a fulfillment lifecycle (Order, Invoice, ...), a support inbox has
# no terminal state -- open/pending/closed are all freely reachable from one
# another (an agent reopens a closed thread, or parks an open one as
# pending), so there is no transition graph to enforce here, only membership
# in VALID_CONVERSATION_STATUSES.

# ── Messages ─────────────────────────────────────────────────────────────────

MESSAGE_DIRECTION_INBOUND = "inbound"
MESSAGE_DIRECTION_OUTBOUND = "outbound"
VALID_MESSAGE_DIRECTIONS = {MESSAGE_DIRECTION_INBOUND, MESSAGE_DIRECTION_OUTBOUND}

SENDER_TYPE_CUSTOMER = "customer"
SENDER_TYPE_AGENT = "agent"
SENDER_TYPE_SYSTEM = "system"

MESSAGE_TYPE_TEXT = "text"
MESSAGE_TYPE_IMAGE = "image"
MESSAGE_TYPE_DOCUMENT = "document"
MESSAGE_TYPE_AUDIO = "audio"
MESSAGE_TYPE_VIDEO = "video"
MESSAGE_TYPE_TEMPLATE = "template"
VALID_MESSAGE_TYPES = {
    MESSAGE_TYPE_TEXT,
    MESSAGE_TYPE_IMAGE,
    MESSAGE_TYPE_DOCUMENT,
    MESSAGE_TYPE_AUDIO,
    MESSAGE_TYPE_VIDEO,
    MESSAGE_TYPE_TEMPLATE,
}
DEFAULT_MESSAGE_TYPE = MESSAGE_TYPE_TEXT

MESSAGE_STATUS_RECEIVED = "received"
MESSAGE_STATUS_QUEUED = "queued"
MESSAGE_STATUS_SENT = "sent"
MESSAGE_STATUS_DELIVERED = "delivered"
MESSAGE_STATUS_READ = "read"
MESSAGE_STATUS_FAILED = "failed"
VALID_MESSAGE_STATUSES = {
    MESSAGE_STATUS_RECEIVED,
    MESSAGE_STATUS_QUEUED,
    MESSAGE_STATUS_SENT,
    MESSAGE_STATUS_DELIVERED,
    MESSAGE_STATUS_READ,
    MESSAGE_STATUS_FAILED,
}

# ── CRM identification mapping ──────────────────────────────────────────────
#
# Maps a channel type to the CRM Customer column used to recognize a
# returning sender, and to the CRM lead source used when GetOrCreate-
# ConversationUseCase auto-creates a Lead for a sender who doesn't match any
# existing Customer. Messenger and SMS have no dedicated Customer field or
# lead source of their own in the CRM domain, so they proxy onto the closest
# existing one (a Facebook profile / a phone number) rather than this module
# inventing a parallel vocabulary CRM doesn't share -- see
# modules.crm.domain.value_objects for the authoritative LEAD_SOURCE_* list.

CHANNEL_CUSTOMER_FIELD = {
    CHANNEL_TYPE_WHATSAPP: "whatsapp",
    CHANNEL_TYPE_INSTAGRAM: "instagram",
    CHANNEL_TYPE_MESSENGER: "facebook",
    CHANNEL_TYPE_EMAIL: "email",
    CHANNEL_TYPE_SMS: "phone",
}

CHANNEL_LEAD_SOURCE = {
    CHANNEL_TYPE_WHATSAPP: "whatsapp",
    CHANNEL_TYPE_INSTAGRAM: "instagram",
    CHANNEL_TYPE_MESSENGER: "messenger",
    CHANNEL_TYPE_EMAIL: "other",
    CHANNEL_TYPE_SMS: "phone_call",
}
