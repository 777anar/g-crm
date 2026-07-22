class InvalidWorkOrderTransitionError(ValueError):
    """Raised when a work order status change doesn't follow the shop-floor transition graph."""


class WorkOrderAlreadyExistsError(ValueError):
    """Raised when creating a work order for an Order that already has one."""


class OrderNotReadyForProductionError(ValueError):
    """Raised when creating a work order for an Order that hasn't reached approved_for_production."""


class NoProductionItemsError(ValueError):
    """Raised when an Order has no slab-linked items to send to production."""


class SlabNotReservedError(ValueError):
    """Raised when a work order tries to start production on a slab that isn't reserved
    (e.g. it was released, sold, or scrapped by something else in the meantime)."""


class InvalidPriorityError(ValueError):
    """Raised when a work order priority isn't one of the valid values."""


class StageNotFoundError(ValueError):
    """Raised when a work order stage transition references a stage id
    that doesn't belong to this company (or has been deleted)."""


class OperatorNotInCompanyError(ValueError):
    """Raised when assigning a work order to a user who isn't a member of the active company."""
