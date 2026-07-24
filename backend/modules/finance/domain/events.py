"""Domain events published by the Finance module."""

INVOICE_CREATED = "InvoiceCreated"
INVOICE_STATUS_CHANGED = "InvoiceStatusChanged"
INVOICE_CANCELLED = "InvoiceCancelled"
PAYMENT_RECEIVED = "PaymentReceived"
EXPENSE_CREATED = "ExpenseCreated"

# Phase 22: online payment collection.
PAYMENT_SESSION_CREATED = "PaymentSessionCreated"
PAYMENT_SESSION_FAILED = "PaymentSessionFailed"
