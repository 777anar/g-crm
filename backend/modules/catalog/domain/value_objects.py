"""Pure value objects/enums for the Stone Catalog module. No framework or
DB imports -- per Clean Architecture, the domain layer knows nothing about
SQLAlchemy or FastAPI."""

# Stone Material lifecycle, per requirements: "Status (Active / Hidden)".
MATERIAL_STATUS_ACTIVE = "active"
MATERIAL_STATUS_HIDDEN = "hidden"
VALID_MATERIAL_STATUSES = {MATERIAL_STATUS_ACTIVE, MATERIAL_STATUS_HIDDEN}
DEFAULT_MATERIAL_STATUS = MATERIAL_STATUS_ACTIVE

# Brands, Collections, Warehouses, and Price Lists share the same simple
# active/hidden lifecycle as Materials -- one vocabulary, reused everywhere
# a catalog entity needs to be retired without deleting its history (slabs,
# price entries, and documents/images all reference these by id).
ENTITY_STATUS_ACTIVE = "active"
ENTITY_STATUS_HIDDEN = "hidden"
VALID_ENTITY_STATUSES = {ENTITY_STATUS_ACTIVE, ENTITY_STATUS_HIDDEN}
DEFAULT_ENTITY_STATUS = ENTITY_STATUS_ACTIVE

# Slab lifecycle -- a physical, individually tracked piece of stone. Phase 1
# of the Purchasing -> Inventory -> Production workflow adds three states
# either side of the original five (received/consumed/offcut_created), so a
# slab's life reads as a real fabrication-shop story: delivered, shelved,
# allocated to a job, cut, and either fully used up or leaving a remnant --
# without touching the meaning or transitions of the five original states,
# so every existing quote/order/work-order flow keeps working unchanged.
SLAB_STATUS_RECEIVED = "received"
SLAB_STATUS_AVAILABLE = "available"
SLAB_STATUS_RESERVED = "reserved"
SLAB_STATUS_IN_PRODUCTION = "in_production"
SLAB_STATUS_OFFCUT_CREATED = "offcut_created"
SLAB_STATUS_CONSUMED = "consumed"
SLAB_STATUS_SOLD = "sold"
SLAB_STATUS_SCRAP = "scrap"
VALID_SLAB_STATUSES = {
    SLAB_STATUS_RECEIVED,
    SLAB_STATUS_AVAILABLE,
    SLAB_STATUS_RESERVED,
    SLAB_STATUS_IN_PRODUCTION,
    SLAB_STATUS_OFFCUT_CREATED,
    SLAB_STATUS_CONSUMED,
    SLAB_STATUS_SOLD,
    SLAB_STATUS_SCRAP,
}
DEFAULT_SLAB_STATUS = SLAB_STATUS_AVAILABLE

# Terminal statuses: once here, a slab's status can never change again via
# `UpdateSlabStatusUseCase`. Production's work-order completion cascade uses
# this to skip a slab that already left the pipeline a different way (e.g.
# an offcut was registered mid-job) instead of raising a transition error.
TERMINAL_SLAB_STATUSES = {
    SLAB_STATUS_OFFCUT_CREATED,
    SLAB_STATUS_CONSUMED,
    SLAB_STATUS_SOLD,
    SLAB_STATUS_SCRAP,
}

# Phase 19 (Stone Fabrication Workflow, Phase 3) closes the "sold vs.
# consumed" ambiguity flagged in MASTER_DEVELOPMENT_ROADMAP.md: `consumed`
# means "physically used up by a completed Production work order" and must
# only ever be system-set (Production's own completion cascade, which calls
# `UpdateSlabStatusUseCase` with `system_triggered=True` -- see
# work_order_use_cases.py's `_cascade_slabs`); a human can never PATCH a
# slab straight to `consumed` via the raw status endpoint. `sold` remains a
# normal user-settable status (a slab can be sold as raw stock, mid-
# reservation, or mid-production) -- see `UpdateSlabStatusUseCase` for the
# companion fix: transitioning a reserved/in_production slab to a terminal
# status the user chose (sold/scrap) now always releases any dangling
# active reservation instead of leaving it stuck `active` forever.
SYSTEM_ONLY_SLAB_STATUSES = {SLAB_STATUS_CONSUMED}

# Slab status transitions a single PATCH is allowed to make. Modeled as a
# directed graph rather than "any status to any status" so the lifecycle
# means something: a consumed slab can't bounce back to available by
# mistake, but a reservation can be released, and scrap is reachable from
# anywhere (a slab can break at any stage).
_VALID_SLAB_TRANSITIONS = {
    SLAB_STATUS_RECEIVED: {SLAB_STATUS_AVAILABLE, SLAB_STATUS_SCRAP},
    SLAB_STATUS_AVAILABLE: {SLAB_STATUS_RESERVED, SLAB_STATUS_IN_PRODUCTION, SLAB_STATUS_SCRAP},
    SLAB_STATUS_RESERVED: {SLAB_STATUS_AVAILABLE, SLAB_STATUS_SOLD, SLAB_STATUS_IN_PRODUCTION, SLAB_STATUS_SCRAP},
    SLAB_STATUS_IN_PRODUCTION: {
        SLAB_STATUS_SOLD,
        SLAB_STATUS_CONSUMED,
        SLAB_STATUS_OFFCUT_CREATED,
        SLAB_STATUS_SCRAP,
        SLAB_STATUS_AVAILABLE,
    },
    SLAB_STATUS_OFFCUT_CREATED: set(),  # terminal
    SLAB_STATUS_CONSUMED: set(),  # terminal
    SLAB_STATUS_SOLD: set(),  # terminal
    SLAB_STATUS_SCRAP: set(),  # terminal
}


def is_valid_slab_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_SLAB_TRANSITIONS.get(current, set())


# Material Reservation lifecycle (Phase 1): a reservation is the durable,
# queryable record of "this slab is allocated to this order item" -- richer
# than the Slab's own `status` field alone, which only tells you a slab
# *is* reserved, not for whom. `active` mirrors the slab currently being
# reserved/in_production; `released` and `consumed` are terminal.
RESERVATION_STATUS_ACTIVE = "active"
RESERVATION_STATUS_RELEASED = "released"
RESERVATION_STATUS_CONSUMED = "consumed"
VALID_RESERVATION_STATUSES = {
    RESERVATION_STATUS_ACTIVE,
    RESERVATION_STATUS_RELEASED,
    RESERVATION_STATUS_CONSUMED,
}


# Product Images, per requirements: "Multiple images, Full resolution,
# Thumbnail, Bookmatch support".
IMAGE_TYPE_GALLERY = "gallery"
IMAGE_TYPE_THUMBNAIL = "thumbnail"
IMAGE_TYPE_BOOKMATCH_LEFT = "bookmatch_left"
IMAGE_TYPE_BOOKMATCH_RIGHT = "bookmatch_right"
VALID_IMAGE_TYPES = {
    IMAGE_TYPE_GALLERY,
    IMAGE_TYPE_THUMBNAIL,
    IMAGE_TYPE_BOOKMATCH_LEFT,
    IMAGE_TYPE_BOOKMATCH_RIGHT,
}

# Documents, per requirements: "Technical PDF, Installation Guide,
# Cleaning Guide".
DOCUMENT_TYPE_TECHNICAL_PDF = "technical_pdf"
DOCUMENT_TYPE_INSTALLATION_GUIDE = "installation_guide"
DOCUMENT_TYPE_CLEANING_GUIDE = "cleaning_guide"
VALID_DOCUMENT_TYPES = {
    DOCUMENT_TYPE_TECHNICAL_PDF,
    DOCUMENT_TYPE_INSTALLATION_GUIDE,
    DOCUMENT_TYPE_CLEANING_GUIDE,
}

# A starter material-type vocabulary for the stone-industry brands named in
# the requirements (NEOLITH, CAESARSTONE, INALCO, ...). Stored as free text
# on the Material record (not a hard enum in the DB) so a company can name a
# material type that isn't in this starter list -- this is just what the
# create-material form offers by default.
SUGGESTED_MATERIAL_TYPES = [
    "Sintered Stone",
    "Porcelain",
    "Quartz",
    "Natural Marble",
    "Natural Granite",
    "Dekton",
    "Ceramic",
]

# Sprint 4: named brands the Brand creation form suggests by default. Same
# "starter vocabulary, not a hard enum" rule as SUGGESTED_MATERIAL_TYPES above
# -- Brand.name stays free text so any company can add a brand not in this
# list. Preparing for a future official supplier-catalog import is exactly
# why this list exists (recognizing these names), not because their
# technical specs are stored anywhere in this codebase.
SUGGESTED_BRANDS = [
    "NEOLITH",
    "MARAZZI THE TOP",
    "SAPIENSTONE",
    "INALCO",
    "ANATOLIA",
    "BELENCO",
    "COANTE",
]
