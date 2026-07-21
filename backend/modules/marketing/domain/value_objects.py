"""Pure value objects for the Marketing module. No framework or DB imports."""

# Reuses the exact same channel vocabulary CRM's Lead.source_channel already
# uses -- a campaign runs on the same channels a lead can arrive through, and
# keeping one shared vocabulary (rather than a second, subtly different one)
# is what makes "which campaign brought this lead in" a meaningful question.
CAMPAIGN_CHANNEL_INSTAGRAM = "instagram"
CAMPAIGN_CHANNEL_FACEBOOK = "facebook"
CAMPAIGN_CHANNEL_MESSENGER = "messenger"
CAMPAIGN_CHANNEL_WHATSAPP = "whatsapp"
CAMPAIGN_CHANNEL_PHONE_CALL = "phone_call"
CAMPAIGN_CHANNEL_WEBSITE = "website"
CAMPAIGN_CHANNEL_OFFICE_VISIT = "office_visit"
CAMPAIGN_CHANNEL_REFERRAL = "referral"
CAMPAIGN_CHANNEL_OTHER = "other"

VALID_CAMPAIGN_CHANNELS = {
    CAMPAIGN_CHANNEL_INSTAGRAM,
    CAMPAIGN_CHANNEL_FACEBOOK,
    CAMPAIGN_CHANNEL_MESSENGER,
    CAMPAIGN_CHANNEL_WHATSAPP,
    CAMPAIGN_CHANNEL_PHONE_CALL,
    CAMPAIGN_CHANNEL_WEBSITE,
    CAMPAIGN_CHANNEL_OFFICE_VISIT,
    CAMPAIGN_CHANNEL_REFERRAL,
    CAMPAIGN_CHANNEL_OTHER,
}

# ── Campaign lifecycle ───────────────────────────────────────────────────────

CAMPAIGN_STATUS_DRAFT = "draft"
CAMPAIGN_STATUS_ACTIVE = "active"
CAMPAIGN_STATUS_COMPLETED = "completed"
CAMPAIGN_STATUS_CANCELLED = "cancelled"

VALID_CAMPAIGN_STATUSES = {
    CAMPAIGN_STATUS_DRAFT,
    CAMPAIGN_STATUS_ACTIVE,
    CAMPAIGN_STATUS_COMPLETED,
    CAMPAIGN_STATUS_CANCELLED,
}

TERMINAL_CAMPAIGN_STATUSES = {CAMPAIGN_STATUS_COMPLETED, CAMPAIGN_STATUS_CANCELLED}

# draft -> active (launched) -> completed (ran its course); cancellable from
# either non-terminal state (e.g. budget pulled before or during the run).
_VALID_CAMPAIGN_TRANSITIONS = {
    CAMPAIGN_STATUS_DRAFT: {CAMPAIGN_STATUS_ACTIVE, CAMPAIGN_STATUS_CANCELLED},
    CAMPAIGN_STATUS_ACTIVE: {CAMPAIGN_STATUS_COMPLETED, CAMPAIGN_STATUS_CANCELLED},
    CAMPAIGN_STATUS_COMPLETED: set(),
    CAMPAIGN_STATUS_CANCELLED: set(),
}


def is_valid_campaign_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_CAMPAIGN_TRANSITIONS.get(current, set())


DEFAULT_CAMPAIGN_CURRENCY = "AZN"

# Order statuses that count as "closed won" for revenue attribution -- an
# order that's merely in progress hasn't generated real revenue yet, and a
# cancelled order never will. Kept here (rather than importing
# modules.orders.domain.value_objects) so Marketing's domain layer has no
# compile-time dependency on another module's domain, matching the same
# choice Finance already made for ORDER_STATUSES_INVOICEABLE.
ORDER_STATUSES_COUNTED_AS_REVENUE = {"ready", "delivered", "installed", "completed"}
