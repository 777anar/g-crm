"""Payment use cases: recording a payment against an Invoice, which is the
only path that ever moves an invoice into partially_paid/paid -- keeping
amount_paid and status from ever drifting apart (see invoice_use_cases.py's
UpdateInvoiceStatusUseCase, which explicitly refuses those two targets)."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.finance.application.dtos import RecordPaymentInput
from modules.finance.domain import events as finance_events
from modules.finance.domain.exceptions import InvalidPaymentAmountError, InvoiceImmutableError, OverpaymentError
from modules.finance.domain.value_objects import (
    INVOICE_STATUS_DRAFT,
    INVOICE_STATUS_PAID,
    INVOICE_STATUS_PARTIALLY_PAID,
    TERMINAL_INVOICE_STATUSES,
)
from modules.finance.infrastructure.models.payment import Payment
from modules.finance.infrastructure.repositories.invoice_repository import InvoiceRepository
from modules.finance.infrastructure.repositories.payment_repository import PaymentRepository

MODULE = "finance"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RecordPaymentUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.invoices = InvoiceRepository(db)
        self.payments = PaymentRepository(db)

    def execute(self, data: RecordPaymentInput) -> Payment:
        invoice = self.invoices.get(company_id=data.company_id, invoice_id=data.invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found")

        if invoice.status == INVOICE_STATUS_DRAFT:
            raise InvoiceImmutableError("Send the invoice before recording a payment against it")
        if invoice.status in TERMINAL_INVOICE_STATUSES:
            raise InvoiceImmutableError(f"Cannot record a payment on a {invoice.status} invoice")

        if data.amount <= 0:
            raise InvalidPaymentAmountError("Payment amount must be positive")
        if data.amount > invoice.balance_due:
            raise OverpaymentError(
                f"Payment of {data.amount} exceeds outstanding balance of {invoice.balance_due}"
            )

        paid_at = data.paid_at or _now()
        payment = Payment(
            company_id=data.company_id,
            invoice_id=invoice.id,
            amount=data.amount,
            method=data.method,
            paid_at=paid_at,
            reference_note=data.reference_note,
            recorded_by=data.actor_user_id,
        )
        self.payments.add(payment)

        old_status = invoice.status
        invoice.amount_paid = invoice.amount_paid + data.amount
        if invoice.amount_paid >= invoice.total_amount:
            invoice.status = INVOICE_STATUS_PAID
            invoice.paid_at = paid_at
        else:
            invoice.status = INVOICE_STATUS_PARTIALLY_PAID

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="payment.recorded",
            entity_type="invoice_payment",
            entity_id=payment.id,
            diff={
                "invoice_id": str(invoice.id),
                "amount": str(data.amount),
                "method": data.method,
                "amount_paid": str(invoice.amount_paid),
            },
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=finance_events.PAYMENT_RECEIVED,
                company_id=data.company_id,
                payload={
                    "invoice_id": str(invoice.id),
                    "payment_id": str(payment.id),
                    "amount": str(data.amount),
                    "amount_paid": str(invoice.amount_paid),
                    "total_amount": str(invoice.total_amount),
                },
                published_by_module=MODULE,
            ),
            self.db,
        )

        if old_status != invoice.status:
            event_bus.publish(
                Event(
                    name=finance_events.INVOICE_STATUS_CHANGED,
                    company_id=data.company_id,
                    payload={"invoice_id": str(invoice.id), "old_status": old_status, "new_status": invoice.status},
                    published_by_module=MODULE,
                ),
                self.db,
            )

        return payment
