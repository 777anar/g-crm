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

# Slab lifecycle -- a physical, individually tracked piece of stone.
SLAB_STATUS_AVAILABLE = "available"
SLAB_STATUS_RESERVED = "reserved"
SLAB_STATUS_SOLD = "sold"
SLAB_STATUS_IN_PRODUCTION = "in_production"
SLAB_STATUS_SCRAP = "scrap"
VALID_SLAB_STATUSES = {
    SLAB_STATUS_AVAILABLE,
    SLAB_STATUS_RESERVED,
    SLAB_STATUS_SOLD,
    SLAB_STATUS_IN_PRODUCTION,
    SLAB_STATUS_SCRAP,
}
DEFAULT_SLAB_STATUS = SLAB_STATUS_AVAILABLE

# Slab status transitions a single PATCH is allowed to make. Modeled as a
# directed graph rather than "any status to any status" so the lifecycle
# means something: a sold slab can't bounce back to available by mistake,
# but a reservation can be released, and scrap is reachable from anywhere
# (a slab can break at any stage).
_VALID_SLAB_TRANSITIONS = {
    SLAB_STATUS_AVAILABLE: {SLAB_STATUS_RESERVED, SLAB_STATUS_IN_PRODUCTION, SLAB_STATUS_SCRAP},
    SLAB_STATUS_RESERVED: {SLAB_STATUS_AVAILABLE, SLAB_STATUS_SOLD, SLAB_STATUS_IN_PRODUCTION, SLAB_STATUS_SCRAP},
    SLAB_STATUS_IN_PRODUCTION: {SLAB_STATUS_SOLD, SLAB_STATUS_SCRAP, SLAB_STATUS_AVAILABLE},
    SLAB_STATUS_SOLD: set(),  # terminal
    SLAB_STATUS_SCRAP: set(),  # terminal
}


def is_valid_slab_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_SLAB_TRANSITIONS.get(current, set())


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
