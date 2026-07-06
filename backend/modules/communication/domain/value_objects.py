"""Pure value objects for the Communication Center module. No framework or
DB imports."""

# ── Channels ─────────────────────────────────────────────────────────────────

CHANNEL_TYPE_WHATSAPP = "whatsapp"
CHANNEL_TYPE_INSTAGRAM = "instagram"
CHANNEL_TYPE_MESSENGER = "messenger"
CHANNEL_TYPE_EMAIL = "email"
CHANNEL_TYPE_SMS = "sms"
VALID_CHANNEL_TYPES = {
    CHANNEL_TYPE_WHATSAPP,
    CHANNEL_TYPE_INSTAGRAM,
    CHANNEL_TYPE_MESSENGER,
    CHANNEL_TYPE_EMAIL,
    CHANNEL_TYPE_SMS,
}

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
MESSAGE_STATUS_SENT = "sent"
MESSAGE_STATUS_DELIVERED = "delivered"
MESSAGE_STATUS_READ = "read"
MESSAGE_STATUS_FAILED = "failed"
VALID_MESSAGE_STATUSES = {
    MESSAGE_STATUS_RECEIVED,
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
