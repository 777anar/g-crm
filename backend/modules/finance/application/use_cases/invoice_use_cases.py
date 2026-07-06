"""Invoice use cases: create from an Order that has reached ready/delivered/
installed/completed (snapshotting its items into invoice lines), send/cancel/
mark-overdue transitions, and edit the mutable fields (due date, notes).

Reuses Orders' and Installation's own repositories to read (never write)
their entities -- Finance never mutates another module's rows, only its own,
matching the read-only cross-module pattern already used by Production and
Installation for their own Order lookups.
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.finance.application.dtos import (
    CreateInvoiceInput,
    UpdateInvoiceInput,
    UpdateInvoiceStatusInput,
)
from modules.finance.domain import events as finance_events
from modules.finance.domain.exceptions import (
    InvalidInvoiceTransitionError,
    InvoiceAlreadyExistsError,
    InvoiceImmutableError,
    OrderNotInvoiceableError,
)
from modules.finance.domain.value_objects import (
    INVOICE_STATUS_CANCELLED,
    INVOICE_STATUS_DRAFT,
    INVOICE_STATUS_SENT,
    MANUALLY_SETTABLE_INVOICE_STATUSES,
    ORDER_STATUSES_INVOICEABLE,
    TERMINAL_INVOICE_STATUSES,
    is_valid_invoice_transition,
)
from modules.finance.infrastructure.models.invoice import Invoice
from modules.finance.infrastructure.models.invoice_line import InvoiceLine
from modules.finance.infrastructure.repositories.invoice_line_repository import InvoiceLineRepository
from modules.finance.infrastructure.repositories.invoice_repository import InvoiceRepository
from modules.installation.infrastructure.repositories.installation_job_repository import (
    InstallationJobRepository,
)
from modules.orders.infrastructure.repositories.order_item_repository import OrderItemRepository
from modules.orders.infrastructure.repositories.order_repository import OrderRepository

MODULE = "finance"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateInvoiceUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.invoices = InvoiceRepository(db)
        self.invoice_lines = InvoiceLineRepository(db)
        self.orders = OrderRepository(db)
        self.order_items = OrderItemRepository(db)
        self.installation_jobs = InstallationJobRepository(db)

    def execute(self, data: CreateInvoiceInput) -> Invoice:
        order = self.orders.get(company_id=data.company_id, order_id=data.order_id)
        if order is None:
            raise NotFoundError("Order not found")

        if order.status not in ORDER_STATUSES_INVOICEABLE:
            raise OrderNotInvoiceableError(
                f"Order must be one of {sorted(ORDER_STATUSES_INVOICEABLE)} to raise an invoice "
                f"(current status: '{order.status}')"
            )

        if self.invoices.get_for_order(company_id=data.company_id, order_id=data.order_id) is not None:
            raise InvoiceAlreadyExistsError("This order already has an invoice")

        items = self.order_items.list_for_order(company_id=data.company_id, order_id=order.id)
        installation_job = self.installation_jobs.get_for_order(company_id=data.company_id, order_id=order.id)

        year = _now().year
        invoice_number = self.invoices.next_invoice_number(company_id=data.company_id, year=year)

        subtotal_amount = sum((item.line_total_sale for item in items), Decimal("0"))

        invoice = Invoice(
            company_id=data.company_id,
            order_id=order.id,
            customer_id=order.customer_id,
            installation_job_id=installation_job.id if installation_job else None,
            invoice_number=invoice_number,
            status=INVOICE_STATUS_DRAFT,
            currency=order.currency,
            subtotal_amount=subtotal_amount,
            total_amount=order.total_final,
            amount_paid=Decimal("0"),
            issue_date=_now().strftime("%Y-%m-%d"),
            due_date=data.due_date,
            notes=data.notes,
            created_by=data.actor_user_id,
        )
        self.invoices.add(invoice)

        for sort_order, item in enumerate(items):
            self.invoice_lines.add(InvoiceLine(
                company_id=data.company_id,
                invoice_id=invoice.id,
                description=item.description,
                amount=item.line_total_sale,
                sort_order=sort_order,
            ))

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="invoice.created",
            entity_type="invoice",
            entity_id=invoice.id,
            diff={"invoice_number": invoice_number, "order_id": str(order.id), "total_amount": str(order.total_final)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=finance_events.INVOICE_CREATED,
                company_id=data.company_id,
                payload={
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice_number,
                    "order_id": str(order.id),
                    "total_amount": str(order.total_final),
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return invoice


class UpdateInvoiceUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.invoices = InvoiceRepository(db)

    def execute(self, data: UpdateInvoiceInput) -> Invoice:
        invoice = self.invoices.get(company_id=data.company_id, invoice_id=data.invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found")

        if invoice.status in TERMINAL_INVOICE_STATUSES:
            raise InvoiceImmutableError(f"Cannot edit a {invoice.status} invoice")

        if data.due_date is not None:
            invoice.due_date = data.due_date
        if data.notes is not None:
            invoice.notes = data.notes

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="invoice.updated",
            entity_type="invoice",
            entity_id=invoice.id,
            diff={"due_date": data.due_date, "notes": data.notes},
        )
        self.db.flush()
        return invoice


class UpdateInvoiceStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.invoices = InvoiceRepository(db)

    def execute(self, data: UpdateInvoiceStatusInput) -> Invoice:
        invoice = self.invoices.get(company_id=data.company_id, invoice_id=data.invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found")

        if data.status not in MANUALLY_SETTABLE_INVOICE_STATUSES:
            raise InvalidInvoiceTransitionError(
                f"Status '{data.status}' cannot be set manually -- it is only ever a side effect of recording a payment"
            )
        if not is_valid_invoice_transition(current=invoice.status, target=data.status):
            raise InvalidInvoiceTransitionError(
                f"Cannot move invoice from '{invoice.status}' to '{data.status}'"
            )

        old_status = invoice.status
        invoice.status = data.status
        now = _now()

        if data.status == INVOICE_STATUS_SENT:
            invoice.sent_at = now
        elif data.status == INVOICE_STATUS_CANCELLED:
            invoice.cancelled_at = now
            invoice.cancelled_reason = data.cancelled_reason

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="invoice.status_changed",
            entity_type="invoice",
            entity_id=invoice.id,
            diff={"status": {"old": old_status, "new": invoice.status}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=finance_events.INVOICE_STATUS_CHANGED,
                company_id=data.company_id,
                payload={"invoice_id": str(invoice.id), "old_status": old_status, "new_status": invoice.status},
                published_by_module=MODULE,
            ),
            self.db,
        )

        if data.status == INVOICE_STATUS_CANCELLED:
            event_bus.publish(
                Event(
                    name=finance_events.INVOICE_CANCELLED,
                    company_id=data.company_id,
                    payload={"invoice_id": str(invoice.id), "reason": data.cancelled_reason},
                    published_by_module=MODULE,
                ),
                self.db,
            )

        return invoice
