"""Pure value objects for the Sales module. No framework/DB imports."""

# ── Project ──────────────────────────────────────────────────────────────────

PROJECT_TYPE_KITCHEN = "kitchen"
PROJECT_TYPE_BATHROOM = "bathroom"
PROJECT_TYPE_COMMERCIAL = "commercial"
PROJECT_TYPE_STAIRS = "stairs"
PROJECT_TYPE_FIREPLACE = "fireplace"
PROJECT_TYPE_OTHER = "other"
VALID_PROJECT_TYPES = {
    PROJECT_TYPE_KITCHEN,
    PROJECT_TYPE_BATHROOM,
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_STAIRS,
    PROJECT_TYPE_FIREPLACE,
    PROJECT_TYPE_OTHER,
}

PROJECT_STATUS_ACTIVE = "active"
PROJECT_STATUS_COMPLETED = "completed"
PROJECT_STATUS_CANCELLED = "cancelled"
VALID_PROJECT_STATUSES = {PROJECT_STATUS_ACTIVE, PROJECT_STATUS_COMPLETED, PROJECT_STATUS_CANCELLED}

# ── Quote ─────────────────────────────────────────────────────────────────────

QUOTE_STATUS_DRAFT = "draft"
QUOTE_STATUS_SENT = "sent"
QUOTE_STATUS_NEGOTIATION = "negotiation"
QUOTE_STATUS_ACCEPTED = "accepted"
QUOTE_STATUS_REJECTED = "rejected"
QUOTE_STATUS_EXPIRED = "expired"

VALID_QUOTE_STATUSES = {
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_SENT,
    QUOTE_STATUS_NEGOTIATION,
    QUOTE_STATUS_ACCEPTED,
    QUOTE_STATUS_REJECTED,
    QUOTE_STATUS_EXPIRED,
}

# Statuses that are immutable (any edit creates a new version instead).
IMMUTABLE_QUOTE_STATUSES = {QUOTE_STATUS_SENT, QUOTE_STATUS_NEGOTIATION, QUOTE_STATUS_ACCEPTED}

# Terminal statuses — once here the quote is done; slabs must be released.
TERMINAL_QUOTE_STATUSES = {QUOTE_STATUS_REJECTED, QUOTE_STATUS_EXPIRED}

# Valid status transitions for a single PATCH.
_VALID_QUOTE_TRANSITIONS = {
    QUOTE_STATUS_DRAFT: {QUOTE_STATUS_SENT, QUOTE_STATUS_REJECTED},
    QUOTE_STATUS_SENT: {QUOTE_STATUS_NEGOTIATION, QUOTE_STATUS_ACCEPTED, QUOTE_STATUS_REJECTED, QUOTE_STATUS_EXPIRED},
    QUOTE_STATUS_NEGOTIATION: {QUOTE_STATUS_SENT, QUOTE_STATUS_ACCEPTED, QUOTE_STATUS_REJECTED, QUOTE_STATUS_EXPIRED},
    QUOTE_STATUS_ACCEPTED: {QUOTE_STATUS_REJECTED},  # cancellation path
    QUOTE_STATUS_REJECTED: set(),  # terminal
    QUOTE_STATUS_EXPIRED: set(),   # terminal
}


def is_valid_quote_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_QUOTE_TRANSITIONS.get(current, set())


# ── Quote section item types ──────────────────────────────────────────────────

ITEM_TYPE_MATERIAL = "material"
ITEM_TYPE_WALL_CLADDING = "wall_cladding"
ITEM_TYPE_VANITY = "vanity"
ITEM_TYPE_BACKSPLASH = "backsplash"
ITEM_TYPE_EDGE_PROFILE = "edge_profile"
ITEM_TYPE_SINK_CUTOUT = "sink_cutout"
ITEM_TYPE_COOKTOP_CUTOUT = "cooktop_cutout"
ITEM_TYPE_FAUCET_HOLE = "faucet_hole"
ITEM_TYPE_INSTALLATION = "installation"
ITEM_TYPE_TRANSPORT = "transport"
ITEM_TYPE_CRANE = "crane"
ITEM_TYPE_OTHER = "other"

VALID_ITEM_TYPES = {
    ITEM_TYPE_MATERIAL,
    ITEM_TYPE_WALL_CLADDING,
    ITEM_TYPE_VANITY,
    ITEM_TYPE_BACKSPLASH,
    ITEM_TYPE_EDGE_PROFILE,
    ITEM_TYPE_SINK_CUTOUT,
    ITEM_TYPE_COOKTOP_CUTOUT,
    ITEM_TYPE_FAUCET_HOLE,
    ITEM_TYPE_INSTALLATION,
    ITEM_TYPE_TRANSPORT,
    ITEM_TYPE_CRANE,
    ITEM_TYPE_OTHER,
}

# Item types that require a material_id from the Catalog.
MATERIAL_ITEM_TYPES = {ITEM_TYPE_MATERIAL, ITEM_TYPE_WALL_CLADDING, ITEM_TYPE_VANITY, ITEM_TYPE_BACKSPLASH}

# Default unit per item type.
ITEM_TYPE_DEFAULT_UNIT = {
    ITEM_TYPE_MATERIAL: "m2",
    ITEM_TYPE_WALL_CLADDING: "m2",
    ITEM_TYPE_VANITY: "m2",
    ITEM_TYPE_BACKSPLASH: "m2",
    ITEM_TYPE_EDGE_PROFILE: "lm",
    ITEM_TYPE_SINK_CUTOUT: "unit",
    ITEM_TYPE_COOKTOP_CUTOUT: "unit",
    ITEM_TYPE_FAUCET_HOLE: "unit",
    ITEM_TYPE_INSTALLATION: "m2",
    ITEM_TYPE_TRANSPORT: "unit",
    ITEM_TYPE_CRANE: "unit",
    ITEM_TYPE_OTHER: "unit",
}

# Company service-price key per item type.
SERVICE_PRICE_KEYS = {
    ITEM_TYPE_EDGE_PROFILE: "edge_profile_per_lm",
    ITEM_TYPE_SINK_CUTOUT: "sink_cutout",
    ITEM_TYPE_COOKTOP_CUTOUT: "cooktop_cutout",
    ITEM_TYPE_FAUCET_HOLE: "faucet_hole",
    ITEM_TYPE_INSTALLATION: "installation_per_m2",
    ITEM_TYPE_TRANSPORT: "transport",
    ITEM_TYPE_CRANE: "crane",
}

VALID_UNITS = {"m2", "lm", "unit"}

# ── Discount ──────────────────────────────────────────────────────────────────

DISCOUNT_TYPE_NONE = "none"
DISCOUNT_TYPE_PERCENT = "percent"
DISCOUNT_TYPE_FIXED = "fixed"
VALID_DISCOUNT_TYPES = {DISCOUNT_TYPE_NONE, DISCOUNT_TYPE_PERCENT, DISCOUNT_TYPE_FIXED}

# ── Reserved section name ─────────────────────────────────────────────────────

LOGISTICS_SECTION_NAME = "Delivery & Logistics"
