"""Domain exceptions for the Sales module."""


class InvalidQuoteTransitionError(ValueError):
    pass


class QuoteImmutableError(ValueError):
    """Raised when editing a sent/accepted quote directly instead of versioning."""
    pass


class SlabConflictError(ValueError):
    """Raised when accepting a quote but an assigned slab is no longer available."""
    pass


class InvalidItemTypeError(ValueError):
    pass


class InvalidUnitError(ValueError):
    pass
