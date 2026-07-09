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

# Project-item ("piece") types -- Sprint 2 ("Layihə" as the primary business
# object): each of these is a physical piece a customer orders (a kitchen
# countertop, an island, ...), as opposed to the billing-only types above
# (edge_profile, sink_cutout, ..., transport, crane) which are service charges
# rather than fabricated pieces.
ITEM_TYPE_COUNTERTOP = "countertop"
ITEM_TYPE_ISLAND = "island"
ITEM_TYPE_TV_PANEL = "tv_panel"
ITEM_TYPE_BATHROOM_FURNITURE = "bathroom_furniture"
ITEM_TYPE_FLOORING = "flooring"
ITEM_TYPE_STAIRS = "stairs"
ITEM_TYPE_TABLE = "table"

# Sprint 3: "Sink" is its own Project Item piece (a whole sink unit), distinct
# from ITEM_TYPE_SINK_CUTOUT above (a cutout *service charge* on a Quote line
# item for cutting a sink hole into an existing countertop piece).
ITEM_TYPE_SINK = "sink"

# Sprint 5 ("Kamin", "Pəncərə altlığı"): a fireplace surround and a window
# sill are both fabricated pieces like any other Project Item.
ITEM_TYPE_FIREPLACE = "fireplace"
ITEM_TYPE_WINDOW_SILL = "window_sill"

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
    ITEM_TYPE_COUNTERTOP,
    ITEM_TYPE_ISLAND,
    ITEM_TYPE_TV_PANEL,
    ITEM_TYPE_BATHROOM_FURNITURE,
    ITEM_TYPE_FLOORING,
    ITEM_TYPE_STAIRS,
    ITEM_TYPE_TABLE,
    ITEM_TYPE_SINK,
    ITEM_TYPE_FIREPLACE,
    ITEM_TYPE_WINDOW_SILL,
}

# Item types that require a material_id from the Catalog.
MATERIAL_ITEM_TYPES = {
    ITEM_TYPE_MATERIAL,
    ITEM_TYPE_WALL_CLADDING,
    ITEM_TYPE_VANITY,
    ITEM_TYPE_BACKSPLASH,
    ITEM_TYPE_COUNTERTOP,
    ITEM_TYPE_ISLAND,
    ITEM_TYPE_TV_PANEL,
    ITEM_TYPE_BATHROOM_FURNITURE,
    ITEM_TYPE_FLOORING,
    ITEM_TYPE_STAIRS,
    ITEM_TYPE_TABLE,
    ITEM_TYPE_SINK,
    ITEM_TYPE_FIREPLACE,
    ITEM_TYPE_WINDOW_SILL,
}

# The curated subset offered by the Project workspace's "Project Item"
# picker -- a Room's ("Məkan"'s) physical pieces ("Məmulat"), as opposed to
# the full item_type vocabulary above (which also includes non-piece
# billing lines like transport/crane, and older types like backsplash/sink
# kept only for backward compatibility with existing Quotes/Items -- not
# removed, just no longer offered in the picker). This is Sprint 5's
# authoritative 12-item list.
PROJECT_ITEM_TYPES = [
    ITEM_TYPE_COUNTERTOP,
    ITEM_TYPE_ISLAND,
    ITEM_TYPE_VANITY,
    ITEM_TYPE_BATHROOM_FURNITURE,
    ITEM_TYPE_TV_PANEL,
    ITEM_TYPE_TABLE,
    ITEM_TYPE_WALL_CLADDING,
    ITEM_TYPE_FLOORING,
    ITEM_TYPE_STAIRS,
    ITEM_TYPE_FIREPLACE,
    ITEM_TYPE_WINDOW_SILL,
    ITEM_TYPE_OTHER,
]

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
    ITEM_TYPE_COUNTERTOP: "m2",
    ITEM_TYPE_ISLAND: "m2",
    ITEM_TYPE_TV_PANEL: "m2",
    ITEM_TYPE_BATHROOM_FURNITURE: "m2",
    ITEM_TYPE_FLOORING: "m2",
    ITEM_TYPE_STAIRS: "m2",
    ITEM_TYPE_TABLE: "m2",
    ITEM_TYPE_SINK: "unit",
    ITEM_TYPE_FIREPLACE: "unit",
    ITEM_TYPE_WINDOW_SILL: "unit",
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

# ── Rooms (Sprint 3: Project workspace) ───────────────────────────────────────
# A Room ("Məkan") is a physical space within a Project. Project Items
# ("Məmulat") belong to a Room; Measurements/Drawings/Photos belong to a
# Project Item. This is a project-planning structure, independent of any
# specific Quote version's Sections (a Quote can be re-priced/re-versioned
# without the underlying Rooms changing).

ROOM_TYPE_KITCHEN = "kitchen"
ROOM_TYPE_BATHROOM = "bathroom"
ROOM_TYPE_LIVING_ROOM = "living_room"
ROOM_TYPE_STAIRCASE = "staircase"
ROOM_TYPE_EXTERIOR = "exterior"
ROOM_TYPE_CUSTOM = "custom"

# Sprint 5 ("Dəhliz", "Eyvan", "Fasad", "Həyət"): split the old catch-all
# "exterior" into the specific outdoor/transitional spaces G-STONE actually
# quotes. ROOM_TYPE_STAIRCASE/EXTERIOR are kept (not removed) for backward
# compatibility with Rooms already saved with those types -- staircase work
# is now modeled as an ITEM_TYPE_STAIRS piece within any Room instead.
ROOM_TYPE_CORRIDOR = "corridor"
ROOM_TYPE_BALCONY = "balcony"
ROOM_TYPE_FACADE = "facade"
ROOM_TYPE_YARD = "yard"

VALID_ROOM_TYPES = {
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_BATHROOM,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_STAIRCASE,
    ROOM_TYPE_EXTERIOR,
    ROOM_TYPE_CUSTOM,
    ROOM_TYPE_CORRIDOR,
    ROOM_TYPE_BALCONY,
    ROOM_TYPE_FACADE,
    ROOM_TYPE_YARD,
}

# The curated subset offered by the Project workspace's "Məkan" picker --
# Sprint 5's authoritative 8-item list. ROOM_TYPE_STAIRCASE/EXTERIOR remain
# valid (see above) but are no longer offered in the picker.
PROJECT_ROOM_TYPES = [
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_BATHROOM,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_CORRIDOR,
    ROOM_TYPE_BALCONY,
    ROOM_TYPE_FACADE,
    ROOM_TYPE_YARD,
    ROOM_TYPE_CUSTOM,
]

# ── Project Item Drawings ──────────────────────────────────────────────────────

DRAWING_TYPE_DWG = "dwg"
DRAWING_TYPE_DXF = "dxf"
DRAWING_TYPE_SKETCH = "sketch"
DRAWING_TYPE_PDF = "pdf"
VALID_DRAWING_TYPES = {DRAWING_TYPE_DWG, DRAWING_TYPE_DXF, DRAWING_TYPE_SKETCH, DRAWING_TYPE_PDF}

# ── Project Item Measurements ─────────────────────────────────────────────────

MEASUREMENT_STATUS_DRAFT = "draft"
MEASUREMENT_STATUS_FINAL = "final"
VALID_MEASUREMENT_STATUSES = {MEASUREMENT_STATUS_DRAFT, MEASUREMENT_STATUS_FINAL}

# ── Project Item Completion ("Təhvil" -- handover to the customer) ────────────
# Distinct from production_status (is it fabricated yet) and
# installation_status (is it fitted on site yet): completion_status tracks
# whether the finished, installed piece has actually been handed over to and
# accepted by the customer.

COMPLETION_STATUS_PENDING = "pending"
COMPLETION_STATUS_DELIVERED = "delivered"
COMPLETION_STATUS_ACCEPTED = "accepted"
VALID_COMPLETION_STATUSES = {
    COMPLETION_STATUS_PENDING,
    COMPLETION_STATUS_DELIVERED,
    COMPLETION_STATUS_ACCEPTED,
}
