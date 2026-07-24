"""Online payment collection (Phase 22) -- the Customer Portal's first
write action. `depends_on=["finance", ...]` already declared in this
module's manifest is what makes calling straight into Finance's own use
cases legitimate: the same "depends_on for access" pattern Reports/Marketing
already use for read-only cross-module queries, extended here to one
specific, narrow write path Finance itself defines and owns."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.config import settings
from core.db.session import get_db
from modules.customer_portal.infrastructure.auth_dependency import CurrentCustomer, get_current_customer
from modules.customer_portal.infrastructure.repositories.portal_query_repository import PortalQueryRepository
from modules.customer_portal.presentation.schemas.portal import (
    CreatePaymentSessionRequest,
    PortalPaymentSessionOut,
    SimulatePaymentSessionRequest,
)
from modules.finance.application.dtos import CreatePaymentSessionInput, SimulatePaymentSessionInput
from modules.finance.application.use_cases.payment_session_use_cases import (
    CreatePaymentSessionUseCase,
    SimulatePaymentSessionUseCase,
)
from modules.finance.domain.exceptions import PaymentSessionAttributionError, PaymentSessionNotPayableError
from modules.finance.infrastructure.repositories.invoice_payment_session_repository import (
    InvoicePaymentSessionRepository,
)

router = APIRouter()


@router.post("/me/invoices/{invoice_id}/pay", response_model=PortalPaymentSessionOut)
def create_payment_session(
    invoice_id: uuid.UUID,
    payload: CreatePaymentSessionRequest,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalPaymentSessionOut:
    # get_my_invoice's own NotFoundError check (company_id + customer_id
    # scoped) doubles as this endpoint's authorization -- the invoice must
    # already be visible to this customer before they can start paying it.
    invoice = PortalQueryRepository(db).get_invoice(
        company_id=current.company_id, customer_id=current.customer_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise NotFoundError("Invoice not found")

    base = settings.frontend_base_url.rstrip("/")
    try:
        session = CreatePaymentSessionUseCase(db).execute(
            CreatePaymentSessionInput(
                company_id=current.company_id,
                customer_id=current.customer_id,
                invoice_id=invoice_id,
                provider_name=payload.provider,
                success_url=f"{base}/portal/invoices/{invoice_id}?payment=success",
                cancel_url=f"{base}/portal/invoices/{invoice_id}?payment=cancelled",
            )
        )
    except (PaymentSessionNotPayableError, PaymentSessionAttributionError) as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(session)
    return PortalPaymentSessionOut.model_validate(session)


@router.get("/me/payment-sessions/{session_id}", response_model=PortalPaymentSessionOut)
def get_payment_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalPaymentSessionOut:
    session = InvoicePaymentSessionRepository(db).get(company_id=current.company_id, session_id=session_id)
    if session is None or session.customer_id != current.customer_id:
        raise NotFoundError("Payment session not found")
    return PortalPaymentSessionOut.model_validate(session)


@router.post("/me/payment-sessions/{session_id}/simulate", response_model=PortalPaymentSessionOut)
def simulate_payment_session(
    session_id: uuid.UUID,
    payload: SimulatePaymentSessionRequest,
    db: Session = Depends(get_db),
    current: CurrentCustomer = Depends(get_current_customer),
) -> PortalPaymentSessionOut:
    try:
        session = SimulatePaymentSessionUseCase(db).execute(
            SimulatePaymentSessionInput(
                company_id=current.company_id,
                customer_id=current.customer_id,
                session_id=session_id,
                outcome=payload.outcome,
            )
        )
    except PaymentSessionNotPayableError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(session)
    return PortalPaymentSessionOut.model_validate(session)
