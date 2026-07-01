"""Domain exceptions for the Orders module."""


class InvalidOrderTransitionError(ValueError):
    pass


class OrderImmutableError(ValueError):
    """Raised when trying to edit an order in a terminal status."""
    pass


class QuoteNotAcceptedError(ValueError):
    """Raised when creating an order from a quote that is not accepted."""
    pass
