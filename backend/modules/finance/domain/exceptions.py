class InvalidInvoiceTransitionError(ValueError):
    """Raised when an invoice status change doesn't follow the transition graph."""


class InvoiceAlreadyExistsError(ValueError):
    """Raised when creating an invoice for an Order that already has one."""


class OrderNotInvoiceableError(ValueError):
    """Raised when creating an invoice for an Order that hasn't reached ready/delivered/installed/completed."""


class InvoiceImmutableError(ValueError):
    """Raised when trying to edit or cancel an invoice that is paid or already cancelled."""


class OverpaymentError(ValueError):
    """Raised when a recorded payment would exceed an invoice's outstanding balance."""


class InvalidPaymentAmountError(ValueError):
    """Raised when a recorded payment amount is zero or negative."""


class InvalidExpenseAmountError(ValueError):
    """Raised when an expense is submitted with a zero or negative amount."""
