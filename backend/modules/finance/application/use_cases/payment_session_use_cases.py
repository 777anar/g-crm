"""Online payment collection (Phase 22): a Customer-Portal-initiated
checkout session against one Invoice's outstanding balance, resolved to an
actual `Payment` (via the existing, unchanged `RecordPaymentUseCase`) only
once a gateway webhook confirms the money genuinely moved -- never from the
browser's own success-redirect, which a customer can reach without having
actually paid (closed tab, back button, or a forged URL)."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.finance.application.dtos import (
    CreatePaymentSessionInput,
    HandlePaymentWebhookInput,
    RecordPaymentInput,
    SimulatePaymentSessionInput,
)
from modules.finance.domain import events as finance_events
from modules.finance.domain.exceptions import PaymentSessionAttributionError, PaymentSessionNotPayableError
from modules.finance.domain.value_objects import (
    PAYMENT_METHOD_CARD,
    PAYMENT_SESSION_STATUS_COMPLETED,
    PAYMENT_SESSION_STATUS_FAILED,
    TERMINAL_INVOICE_STATUSES,
    TERMINAL_PAYMENT_SESSION_STATUSES,
)
from modules.finance.infrastructure.models.invoice_payment_session import InvoicePaymentSession
from modules.finance.infrastructure.providers.base import (
    PAYMENT_SESSION_STATUS_COMPLETED as PROVIDER_STATUS_COMPLETED,
    PAYMENT_SESSION_STATUS_FAILED as PROVIDER_STATUS_FAILED,
)
from modules.finance.infrastructure.providers.registry import get_payment_gateway_provider
from modules.finance.infrastructure.repositories.invoice_payment_session_repository import (
    InvoicePaymentSessionRepository,
)
from modules.finance.infrastructure.repositories.invoice_repository import InvoiceRepository

from .payment_use_cases import RecordPaymentUseCase

MODULE = "finance"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _invoice_creator_or_raise(invoice) -> None:
    if invoice.created_by is None:
        # AuditLog.actor_user_id is NOT NULL -- a gateway-webhook-originated
        # write is attributed to whoever created the invoice, since there's
        # no authenticated staff user for a customer/gateway callback. Same
        # guard as Communication's channel-webhook attribution.
        raise PaymentSessionAttributionError(
            "This invoice has no created_by user to attribute a gateway-originated payment to"
        )


class CreatePaymentSessionUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.invoices = InvoiceRepository(db)
        self.sessions = InvoicePaymentSessionRepository(db)

    def execute(self, data: CreatePaymentSessionInput) -> InvoicePaymentSession:
        invoice = self.invoices.get(company_id=data.company_id, invoice_id=data.invoice_id)
        if invoice is None or invoice.customer_id != data.customer_id:
            raise NotFoundError("Invoice not found")

        if invoice.status in TERMINAL_INVOICE_STATUSES or invoice.balance_due <= 0:
            raise PaymentSessionNotPayableError("This invoice has no outstanding balance to pay")

        _invoice_creator_or_raise(invoice)

        provider = get_payment_gateway_provider(data.provider_name)
        # A placeholder row's own id is the idempotency/metadata reference
        # handed to the provider -- generated before the provider call so a
        # webhook can always be correlated back to this row even if the
        # provider's own session id needed a moment to record.
        session = InvoicePaymentSession(
            company_id=data.company_id,
            invoice_id=invoice.id,
            customer_id=data.customer_id,
            provider=provider.name,
            provider_session_id="",
            amount=invoice.balance_due,
            currency=invoice.currency,
            checkout_url="",
        )
        self.sessions.add(session)

        result = provider.create_checkout_session(
            provider_session_reference=str(session.id),
            amount=session.amount,
            currency=session.currency,
            description=f"Invoice {invoice.invoice_number}",
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
        session.provider_session_id = result.provider_session_id
        session.checkout_url = result.checkout_url

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=invoice.created_by,
            action="payment_session.created",
            entity_type="invoice_payment_session",
            entity_id=session.id,
            diff={"invoice_id": str(invoice.id), "amount": str(session.amount), "provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=finance_events.PAYMENT_SESSION_CREATED,
                company_id=data.company_id,
                payload={"session_id": str(session.id), "invoice_id": str(invoice.id), "provider": provider.name},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return session


class SimulatePaymentSessionUseCase:
    """Mock-provider-only convenience so the whole payment flow is demoable
    without real Stripe credentials -- rejects outright for any other
    provider, since a real gateway's outcome must only ever come from its
    own signed webhook (see HandlePaymentGatewayWebhookUseCase)."""

    def __init__(self, db: Session):
        self.db = db
        self.sessions = InvoicePaymentSessionRepository(db)
        self.invoices = InvoiceRepository(db)

    def execute(self, data: SimulatePaymentSessionInput) -> InvoicePaymentSession:
        session = self.sessions.get(company_id=data.company_id, session_id=data.session_id)
        if session is None or session.customer_id != data.customer_id:
            raise NotFoundError("Payment session not found")
        if session.provider != "mock":
            raise PaymentSessionNotPayableError("Only mock payment sessions can be simulated")
        if session.status in TERMINAL_PAYMENT_SESSION_STATUSES:
            return session

        invoice = self.invoices.get(company_id=data.company_id, invoice_id=session.invoice_id)
        if data.outcome == PAYMENT_SESSION_STATUS_COMPLETED:
            _invoice_creator_or_raise(invoice)
            payment = RecordPaymentUseCase(self.db).execute(
                RecordPaymentInput(
                    company_id=data.company_id,
                    actor_user_id=invoice.created_by,
                    invoice_id=invoice.id,
                    amount=session.amount,
                    method=PAYMENT_METHOD_CARD,
                    paid_at=_now(),
                    reference_note=f"Online payment via {session.provider} (session {session.id})",
                )
            )
            session.status = PAYMENT_SESSION_STATUS_COMPLETED
            session.payment_id = payment.id
            session.completed_at = _now()
        else:
            session.status = PAYMENT_SESSION_STATUS_FAILED

        self.db.flush()
        return session


class HandlePaymentGatewayWebhookUseCase:
    """The only path a real gateway's outcome can reach an Invoice through.
    Idempotent: a gateway may retry a webhook delivery, and this must not
    double-record a payment for the same session."""

    def __init__(self, db: Session):
        self.db = db
        self.sessions = InvoicePaymentSessionRepository(db)
        self.invoices = InvoiceRepository(db)

    def execute(self, data: HandlePaymentWebhookInput) -> None:
        provider = get_payment_gateway_provider(data.provider_name)
        event = provider.parse_webhook_event(raw_body=data.raw_body, signature_header=data.signature_header)

        session = self.sessions.get_by_provider_session_id(
            provider=provider.name, provider_session_id=event.provider_session_id
        )
        if session is None:
            # Nothing of ours to update (e.g. an event type this integration
            # doesn't track) -- webhooks must still 200 so the gateway
            # doesn't retry forever.
            return
        if session.status in TERMINAL_PAYMENT_SESSION_STATUSES:
            return

        invoice = self.invoices.get(company_id=session.company_id, invoice_id=session.invoice_id)
        if invoice is None:
            return

        if event.status == PROVIDER_STATUS_COMPLETED:
            _invoice_creator_or_raise(invoice)
            payment = RecordPaymentUseCase(self.db).execute(
                RecordPaymentInput(
                    company_id=session.company_id,
                    actor_user_id=invoice.created_by,
                    invoice_id=invoice.id,
                    amount=session.amount,
                    method=PAYMENT_METHOD_CARD,
                    paid_at=_now(),
                    reference_note=f"Online payment via {session.provider} (session {session.id})",
                )
            )
            session.status = PAYMENT_SESSION_STATUS_COMPLETED
            session.payment_id = payment.id
            session.completed_at = _now()
        elif event.status == PROVIDER_STATUS_FAILED:
            session.status = PAYMENT_SESSION_STATUS_FAILED
            event_bus.publish(
                Event(
                    name=finance_events.PAYMENT_SESSION_FAILED,
                    company_id=session.company_id,
                    payload={"session_id": str(session.id), "invoice_id": str(invoice.id)},
                    published_by_module=MODULE,
                ),
                self.db,
            )
        # else "other" -- an event this integration doesn't act on -- leave
        # the session pending.

        self.db.flush()
