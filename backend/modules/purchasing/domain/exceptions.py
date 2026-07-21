class InvalidPurchaseOrderTransitionError(ValueError):
    """Raised when a purchase order status change doesn't follow the transition graph."""


class PurchaseOrderImmutableError(ValueError):
    """Raised when trying to edit a purchase order that is no longer draft."""


class SupplierInactiveError(ValueError):
    """Raised when creating a purchase order against a hidden (inactive) supplier."""


class EmptyPurchaseOrderError(ValueError):
    """Raised when creating a purchase order with no line items."""


class PurchaseOrderNotReceivableError(ValueError):
    """Raised when receiving against an order that isn't confirmed/partially_received."""


class InvalidReceiptQuantityError(ValueError):
    """Raised when a receipt quantity is zero/negative, or would exceed the line's ordered quantity."""


class ReceivedLineHasNoMaterialError(ValueError):
    """Raised when slab details are provided to receive a line that has no linked catalog material."""
