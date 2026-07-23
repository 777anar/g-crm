class CatalogDomainError(Exception):
    pass


class InvalidSlabTransitionError(CatalogDomainError):
    pass


class DuplicateSlabNumberError(CatalogDomainError):
    pass


class SlabAlreadyReservedError(CatalogDomainError):
    """Raised when a slab is requested for reservation but is already
    actively reserved for a different order item -- the double-booking
    guard Material Reservation exists to enforce."""


class SlabNotReservableError(CatalogDomainError):
    """Raised when a slab isn't in a status that can become reserved
    (e.g. it's still `received` and hasn't been shelved into stock yet,
    or it's already in_production/consumed/scrapped)."""


class SlabNotInProductionError(CatalogDomainError):
    """Raised when registering an offcut against a slab that isn't
    currently `in_production` -- an offcut can only come from a slab
    actively being cut."""


class OffcutTooLargeError(CatalogDomainError):
    """Raised when a registered offcut's dimensions don't plausibly fit
    within its parent slab (in either orientation) -- a data-entry
    plausibility check, not a physical measurement (Phase 19)."""


class SlabStatusRequiresSystemActionError(CatalogDomainError):
    """Raised when a manual status PATCH targets a status that may only be
    reached automatically (currently just `consumed`, set exclusively by
    Production's work-order-completion cascade) -- see
    `SYSTEM_ONLY_SLAB_STATUSES` (Phase 19)."""
