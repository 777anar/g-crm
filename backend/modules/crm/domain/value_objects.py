"""Pure value objects/enums. No framework or DB imports -- per Clean
Architecture, the domain layer knows nothing about SQLAlchemy or FastAPI."""

CUSTOMER_TYPE_INDIVIDUAL = "individual"
CUSTOMER_TYPE_BUSINESS = "business"
VALID_CUSTOMER_TYPES = {CUSTOMER_TYPE_INDIVIDUAL, CUSTOMER_TYPE_BUSINESS}

# "Lead Management" channels, per Phase 2 requirements. WhatsApp is included
# now (future-ready) even though no inbound webhook integration exists yet --
# the enum value and manual-entry path both work today; an automated
# WhatsApp ingestion path is a later, additive change to the same field.
LEAD_SOURCE_INSTAGRAM = "instagram"
LEAD_SOURCE_FACEBOOK = "facebook"
LEAD_SOURCE_MESSENGER = "messenger"
LEAD_SOURCE_WHATSAPP = "whatsapp"
LEAD_SOURCE_MANUAL = "manual"
VALID_LEAD_SOURCES = {
    LEAD_SOURCE_INSTAGRAM,
    LEAD_SOURCE_FACEBOOK,
    LEAD_SOURCE_MESSENGER,
    LEAD_SOURCE_WHATSAPP,
    LEAD_SOURCE_MANUAL,
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
