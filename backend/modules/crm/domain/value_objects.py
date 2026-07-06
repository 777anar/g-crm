"""Pure value objects/enums. No framework or DB imports -- per Clean
Architecture, the domain layer knows nothing about SQLAlchemy or FastAPI."""

CUSTOMER_TYPE_INDIVIDUAL = "individual"
CUSTOMER_TYPE_BUSINESS = "business"
VALID_CUSTOMER_TYPES = {CUSTOMER_TYPE_INDIVIDUAL, CUSTOMER_TYPE_BUSINESS}

# Lead sources, customized for the G-STONE GALLERY stone-industry workflow
# (Phase 3). Shared by both the Lead capture channel field and the
# Customer "Lead Source" field -- one vocabulary, since a lead's source
# channel becomes the resulting customer's lead source on conversion.
LEAD_SOURCE_INSTAGRAM = "instagram"
LEAD_SOURCE_FACEBOOK = "facebook"
LEAD_SOURCE_MESSENGER = "messenger"
LEAD_SOURCE_WHATSAPP = "whatsapp"
LEAD_SOURCE_PHONE_CALL = "phone_call"
LEAD_SOURCE_WEBSITE = "website"
LEAD_SOURCE_OFFICE_VISIT = "office_visit"
LEAD_SOURCE_REFERRAL = "referral"
LEAD_SOURCE_OTHER = "other"
VALID_LEAD_SOURCES = {
    LEAD_SOURCE_INSTAGRAM,
    LEAD_SOURCE_FACEBOOK,
    LEAD_SOURCE_MESSENGER,
    LEAD_SOURCE_WHATSAPP,
    LEAD_SOURCE_PHONE_CALL,
    LEAD_SOURCE_WEBSITE,
    LEAD_SOURCE_OFFICE_VISIT,
    LEAD_SOURCE_REFERRAL,
    LEAD_SOURCE_OTHER,
}

LEAD_STATUS_NEW = "new"
LEAD_STATUS_CONTACTED = "contacted"
LEAD_STATUS_QUALIFIED = "qualified"
LEAD_STATUS_CONVERTED = "converted"
LEAD_STATUS_DISQUALIFIED = "disqualified"
VALID_LEAD_STATUSES = {
    LEAD_STATUS_NEW,
    LEAD_STATUS_CONTACTED,
    LEAD_STATUS_QUALIFIED,
    LEAD_STATUS_CONVERTED,
    LEAD_STATUS_DISQUALIFIED,
}

# Stone-industry sales pipeline status (Phase 3 / G-STONE GALLERY
# customization). Ordered list reflects the real workflow stage sequence
# (used for display ordering); CUSTOMER_STATUS_LOST is a terminal state
# reachable from any stage, not a sequential step.
CUSTOMER_STATUS_NEW_INQUIRY = "new_inquiry"
CUSTOMER_STATUS_CONTACTED = "contacted"
CUSTOMER_STATUS_MEASUREMENT_SCHEDULED = "measurement_scheduled"
CUSTOMER_STATUS_MEASUREMENT_COMPLETED = "measurement_completed"
CUSTOMER_STATUS_PREPARING_QUOTE = "preparing_quote"
CUSTOMER_STATUS_QUOTE_SENT = "quote_sent"
CUSTOMER_STATUS_WAITING_FOR_DECISION = "waiting_for_decision"
CUSTOMER_STATUS_APPROVED = "approved"
CUSTOMER_STATUS_PAYMENT_RECEIVED = "payment_received"
CUSTOMER_STATUS_IN_PRODUCTION = "in_production"
CUSTOMER_STATUS_INSTALLATION_SCHEDULED = "installation_scheduled"
CUSTOMER_STATUS_INSTALLED = "installed"
CUSTOMER_STATUS_COMPLETED = "completed"
CUSTOMER_STATUS_LOST = "lost"

CUSTOMER_STATUS_ORDER = [
    CUSTOMER_STATUS_NEW_INQUIRY,
    CUSTOMER_STATUS_CONTACTED,
    CUSTOMER_STATUS_MEASUREMENT_SCHEDULED,
    CUSTOMER_STATUS_MEASUREMENT_COMPLETED,
    CUSTOMER_STATUS_PREPARING_QUOTE,
    CUSTOMER_STATUS_QUOTE_SENT,
    CUSTOMER_STATUS_WAITING_FOR_DECISION,
    CUSTOMER_STATUS_APPROVED,
    CUSTOMER_STATUS_PAYMENT_RECEIVED,
    CUSTOMER_STATUS_IN_PRODUCTION,
    CUSTOMER_STATUS_INSTALLATION_SCHEDULED,
    CUSTOMER_STATUS_INSTALLED,
    CUSTOMER_STATUS_COMPLETED,
    CUSTOMER_STATUS_LOST,
]
VALID_CUSTOMER_STATUSES = set(CUSTOMER_STATUS_ORDER)
DEFAULT_CUSTOMER_STATUS = CUSTOMER_STATUS_NEW_INQUIRY

ACTIVITY_TYPE_NOTE = "note"
ACTIVITY_TYPE_CALL = "call"
ACTIVITY_TYPE_EMAIL = "email"
ACTIVITY_TYPE_MEETING = "meeting"
ACTIVITY_TYPE_SYSTEM = "system"
VALID_ACTIVITY_TYPES = {
    ACTIVITY_TYPE_NOTE,
    ACTIVITY_TYPE_CALL,
    ACTIVITY_TYPE_EMAIL,
    ACTIVITY_TYPE_MEETING,
    ACTIVITY_TYPE_SYSTEM,
}

# ── Tasks & Reminders (Version 1.2) ─────────────────────────────────────────────

TASK_STATUS_PENDING = "pending"
TASK_STATUS_IN_PROGRESS = "in_progress"
TASK_STATUS_DONE = "done"
TASK_STATUS_CANCELLED = "cancelled"
VALID_TASK_STATUSES = {
    TASK_STATUS_PENDING,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_DONE,
    TASK_STATUS_CANCELLED,
}
TERMINAL_TASK_STATUSES = {TASK_STATUS_DONE, TASK_STATUS_CANCELLED}
DEFAULT_TASK_STATUS = TASK_STATUS_PENDING

# A task bounces freely between pending/in_progress right up until it's
# closed out -- unlike a shop-floor or invoice lifecycle, there's no reason
# to forbid a rep moving a task back to "pending" (got interrupted, picking
# it back up later).
_VALID_TASK_TRANSITIONS = {
    TASK_STATUS_PENDING: {TASK_STATUS_IN_PROGRESS, TASK_STATUS_DONE, TASK_STATUS_CANCELLED},
    TASK_STATUS_IN_PROGRESS: {TASK_STATUS_PENDING, TASK_STATUS_DONE, TASK_STATUS_CANCELLED},
    TASK_STATUS_DONE: set(),
    TASK_STATUS_CANCELLED: set(),
}


def is_valid_task_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_TASK_TRANSITIONS.get(current, set())


TASK_PRIORITY_LOW = "low"
TASK_PRIORITY_MEDIUM = "medium"
TASK_PRIORITY_HIGH = "high"
TASK_PRIORITY_URGENT = "urgent"
VALID_TASK_PRIORITIES = {TASK_PRIORITY_LOW, TASK_PRIORITY_MEDIUM, TASK_PRIORITY_HIGH, TASK_PRIORITY_URGENT}
DEFAULT_TASK_PRIORITY = TASK_PRIORITY_MEDIUM

# A task's related_entity_type is intentionally an unvalidated free string
# (like core.audit_log's entity_type) rather than a fixed CHECK-style enum --
# it needs to reference whatever kind of record exists in this deployment
# (customer, lead, order, quote, project, ...) without Tasks' domain layer
# having to know the full set of every other module's entity names.
TASK_RECURRENCE_DAILY = "daily"
TASK_RECURRENCE_WEEKLY = "weekly"
TASK_RECURRENCE_MONTHLY = "monthly"
TASK_RECURRENCE_YEARLY = "yearly"
VALID_TASK_RECURRENCE_RULES = {
    TASK_RECURRENCE_DAILY,
    TASK_RECURRENCE_WEEKLY,
    TASK_RECURRENCE_MONTHLY,
    TASK_RECURRENCE_YEARLY,
}

NOTIFICATION_TYPE_TASK_ASSIGNED = "task_assigned"
NOTIFICATION_TYPE_TASK_REASSIGNED = "task_reassigned"
NOTIFICATION_TYPE_TASK_REMINDER = "task_reminder"
NOTIFICATION_TYPE_TASK_OVERDUE = "task_overdue"
VALID_TASK_NOTIFICATION_TYPES = {
    NOTIFICATION_TYPE_TASK_ASSIGNED,
    NOTIFICATION_TYPE_TASK_REASSIGNED,
    NOTIFICATION_TYPE_TASK_REMINDER,
    NOTIFICATION_TYPE_TASK_OVERDUE,
}
