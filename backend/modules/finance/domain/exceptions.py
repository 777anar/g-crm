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


class PaymentSessionNotPayableError(ValueError):
    """Raised when starting a checkout session against an invoice that's
    draft, cancelled, already fully paid, or already has a pending session."""


class PaymentSessionAttributionError(ValueError):
    """Raised when a gateway-webhook-originated payment can't be attributed
    to an audit actor because the invoice has no `created_by` -- mirrors
    Communication's identical guard for channel webhooks with no configuring
    user (see webhook_use_cases.py's `_load_channel_and_credential`)."""
