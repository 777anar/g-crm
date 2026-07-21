"""Pure value objects for the Purchasing module. No framework or DB imports."""

# ── Supplier status (active/hidden, same pattern as Catalog Brand/Warehouse) ──

SUPPLIER_STATUS_ACTIVE = "active"
SUPPLIER_STATUS_HIDDEN = "hidden"

VALID_SUPPLIER_STATUSES = {SUPPLIER_STATUS_ACTIVE, SUPPLIER_STATUS_HIDDEN}
DEFAULT_SUPPLIER_STATUS = SUPPLIER_STATUS_ACTIVE

# ── Purchase order lifecycle ─────────────────────────────────────────────────

PO_STATUS_DRAFT = "draft"
PO_STATUS_SENT = "sent"
PO_STATUS_CONFIRMED = "confirmed"
PO_STATUS_PARTIALLY_RECEIVED = "partially_received"
PO_STATUS_RECEIVED = "received"
PO_STATUS_CANCELLED = "cancelled"

VALID_PURCHASE_ORDER_STATUSES = {
    PO_STATUS_DRAFT,
    PO_STATUS_SENT,
    PO_STATUS_CONFIRMED,
    PO_STATUS_PARTIALLY_RECEIVED,
    PO_STATUS_RECEIVED,
    PO_STATUS_CANCELLED,
}

TERMINAL_PURCHASE_ORDER_STATUSES = {PO_STATUS_RECEIVED, PO_STATUS_CANCELLED}

# draft -> sent -> confirmed (manual actions) -> partially_received/received
# (driven exclusively by ReceivePurchaseOrderLineUseCase, mirroring Finance's
# invoice partially_paid/paid pattern) -- cancellable from any non-terminal
# state.
_VALID_PURCHASE_ORDER_TRANSITIONS = {
    PO_STATUS_DRAFT: {PO_STATUS_SENT, PO_STATUS_CANCELLED},
    PO_STATUS_SENT: {PO_STATUS_CONFIRMED, PO_STATUS_CANCELLED},
    PO_STATUS_CONFIRMED: {PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_RECEIVED, PO_STATUS_CANCELLED},
    PO_STATUS_PARTIALLY_RECEIVED: {PO_STATUS_RECEIVED, PO_STATUS_CANCELLED},
    PO_STATUS_RECEIVED: set(),
    PO_STATUS_CANCELLED: set(),
}


def is_valid_purchase_order_transition(*, current: str, target: str) -> bool:
    if current == target:
        return True
    return target in _VALID_PURCHASE_ORDER_TRANSITIONS.get(current, set())


# The manual "change status" endpoint only ever drives these three targets --
# partially_received/received are exclusively a side effect of
# ReceivePurchaseOrderLineUseCase, so a line's quantity_received and the
# order's status can never drift apart.
MANUALLY_SETTABLE_PURCHASE_ORDER_STATUSES = {PO_STATUS_SENT, PO_STATUS_CONFIRMED, PO_STATUS_CANCELLED}

# Only a draft order's lines/notes/expected-delivery-date may still change --
# once sent to a supplier, the document is a real, external commitment.
PURCHASE_ORDER_STATUSES_EDITABLE = {PO_STATUS_DRAFT}

# A line can only be received against an order that a supplier has actually
# confirmed -- receiving against draft/sent (nothing agreed yet) or
# received/cancelled (already resolved) makes no business sense.
PURCHASE_ORDER_STATUSES_RECEIVABLE = {PO_STATUS_CONFIRMED, PO_STATUS_PARTIALLY_RECEIVED}

DEFAULT_PURCHASE_ORDER_CURRENCY = "AZN"
