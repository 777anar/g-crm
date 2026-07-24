class CutOptimizationDomainError(Exception):
    pass


class InvalidOptimizationInputError(CutOptimizationDomainError):
    """Raised when slab dimensions, kerf, or the piece list are invalid
    (e.g. zero/negative dimensions, an empty piece list)."""


class NoSlabDimensionsProvidedError(CutOptimizationDomainError):
    """Raised when neither a slab_id nor explicit slab_length_mm/slab_width_mm were given."""


class NoSlabsAvailableError(CutOptimizationDomainError):
    """Raised by a batch run (Phase 20) when no explicit `slab_ids` were
    given and auto-selection found zero available slabs/offcuts matching
    the requested material."""
