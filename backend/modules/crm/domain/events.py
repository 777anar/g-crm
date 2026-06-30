"""Domain events the CRM module publishes. These are the authoritative
definitions per the frozen EDA architecture -- other modules subscribe to
these names without importing CRM's code."""

CUSTOMER_CREATED = "CustomerCreated"
CUSTOMER_UPDATED = "CustomerUpdated"
CUSTOMER_ARCHIVED = "CustomerArchived"
LEAD_CREATED = "LeadCreated"
LEAD_CONVERTED = "LeadConverted"
CUSTOMER_NOTE_ADDED = "CustomerNoteAdded"
CUSTOMER_STATUS_CHANGED = "CustomerStatusChanged"
