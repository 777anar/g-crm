"""Pure value objects for the Finance module. No framework or DB imports."""

# ── Invoice lifecycle ────────────────────────────────────────────────────────

INVOICE_STATUS_DRAFT = "draft"
INVOICE_STATUS_SENT = "sent"
INVOICE_STATUS_PARTIALLY_PAID = "partially_paid"
INVOICE_STATUS_PAID = "paid"
INVOICE_STATUS_OVERDUE = "overdue"
INVOICE_STATUS_CANCELLED = "cancelled"

VALID_INVOICE_STATUSES = {
    INVOICE_STATUS_DRAFT,
    INVOICE_STATUS_SENT,
    INVOICE_STATUS_PARTIALLY_PAID,
    INVOICE_STATUS_PAID,
    INVOICE_STATUS_OVERDUE,
    INVOICE_STATUS_CANCELLED,
}

TERMINAL_INVOICE_STATUSES = {INVOICE_STATUS_PAID, INVOICE_STATUS_CANCELLED}

# draft -> sent (manual "send" action) -> partially_paid/paid (driven by
# RecordPaymentUseCase) or overdue (manual, once past due_date) -- cancellable
# from any non-terminal state. partially_paid/overdue can still resolve to
# paid as further payments arrive.
_VALID_INVOICE_TRANSITIONS = {
    INVOICE_STATUS_DRAFT: {INVOICE_STATUS_SENT, INVOICE_STATUS_CANCELLED},
    INVOICE_STATUS_SENT: {
        INVOICE_STATUS_PARTIALLY_PAID,
        INVOICE_STATUS_PAID,
        INVOICE_STATUS_OVERDUE,
        INVOICE_STATUS_CANCELLED,
    },
    INVOICE_STATUS_PARTIALLY_PAID: {
        INVOICE_STATUS_PAID,
        INVOICE_STATUS_OVERDUE,
        INVOICE_STATUS_CANCELLED,
    },
    INVOICE_STATUS_OVERDUE: {
        INVOICE_STATUS_PARTIALLY_PAID,
        INVOICE_STATUS_PAID,
        INVOICE_STATUS_CANCELLED,
    },
    INVOICE_STATUS_PAID: set(),
    INVOICE_STATUS_CANCELLED: set(),
}


def is_valid_invoice_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_INVOICE_TRANSITIONS.get(current, set())


# The manual "change status" endpoint only ever drives these three targets --
# paid/partially_paid are exclusively a side effect of RecordPaymentUseCase,
# so amount_paid and status can never drift apart.
MANUALLY_SETTABLE_INVOICE_STATUSES = {
    INVOICE_STATUS_SENT,
    INVOICE_STATUS_OVERDUE,
    INVOICE_STATUS_CANCELLED,
}


# Order statuses from which an invoice may be raised -- once fabrication is
# done and the job is at least ready to leave the shop. Kept here (rather
# than importing modules.orders.domain.value_objects) so Finance's domain
# layer has no compile-time dependency on another module's domain; the
# application layer is where the actual cross-module read happens.
ORDER_STATUSES_INVOICEABLE = {"ready", "delivered", "installed", "completed"}

# ── Payments ─────────────────────────────────────────────────────────────────

PAYMENT_METHOD_CASH = "cash"
PAYMENT_METHOD_BANK_TRANSFER = "bank_transfer"
PAYMENT_METHOD_CARD = "card"
PAYMENT_METHOD_CHECK = "check"
PAYMENT_METHOD_OTHER = "other"

VALID_PAYMENT_METHODS = {
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_CHECK,
    PAYMENT_METHOD_OTHER,
}

# ── Expenses ─────────────────────────────────────────────────────────────────

EXPENSE_CATEGORY_MATERIALS = "materials"
EXPENSE_CATEGORY_LABOR = "labor"
EXPENSE_CATEGORY_TRANSPORT = "transport"
EXPENSE_CATEGORY_UTILITIES = "utilities"
EXPENSE_CATEGORY_RENT = "rent"
EXPENSE_CATEGORY_OTHER = "other"

VALID_EXPENSE_CATEGORIES = {
    EXPENSE_CATEGORY_MATERIALS,
    EXPENSE_CATEGORY_LABOR,
    EXPENSE_CATEGORY_TRANSPORT,
    EXPENSE_CATEGORY_UTILITIES,
    EXPENSE_CATEGORY_RENT,
    EXPENSE_CATEGORY_OTHER,
}

# ── Payment sessions (Phase 22: online payment collection) ──────────────────
# A session tracks one Customer-Portal-initiated checkout attempt against one
# Invoice's full outstanding balance -- separate from `Payment` (which only
# ever represents money actually received) so a customer abandoning checkout,
# or a gateway reporting failure, never touches `Invoice.amount_paid`/status.

PAYMENT_SESSION_STATUS_PENDING = "pending"
PAYMENT_SESSION_STATUS_COMPLETED = "completed"
PAYMENT_SESSION_STATUS_FAILED = "failed"

VALID_PAYMENT_SESSION_STATUSES = {
    PAYMENT_SESSION_STATUS_PENDING,
    PAYMENT_SESSION_STATUS_COMPLETED,
    PAYMENT_SESSION_STATUS_FAILED,
}

TERMINAL_PAYMENT_SESSION_STATUSES = {PAYMENT_SESSION_STATUS_COMPLETED, PAYMENT_SESSION_STATUS_FAILED}
