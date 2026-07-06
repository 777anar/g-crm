import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.finance.application.dtos import (
    CreateInvoiceInput,
    RecordPaymentInput,
    UpdateInvoiceInput,
    UpdateInvoiceStatusInput,
)
from modules.finance.application.use_cases import (
    CreateInvoiceUseCase,
    RecordPaymentUseCase,
    UpdateInvoiceStatusUseCase,
    UpdateInvoiceUseCase,
)
from modules.finance.domain.exceptions import (
    InvalidInvoiceTransitionError,
    InvalidPaymentAmountError,
    InvoiceAlreadyExistsError,
    InvoiceImmutableError,
    OrderNotInvoiceableError,
    OverpaymentError,
)
from modules.finance.infrastructure.repositories.invoice_line_repository import InvoiceLineRepository
from modules.finance.infrastructure.repositories.invoice_repository import InvoiceRepository
from modules.finance.infrastructure.repositories.payment_repository import PaymentRepository
from modules.finance.presentation.schemas.finance import (
    InvoiceCreate,
    InvoiceLineListOut,
    InvoiceLineOut,
    InvoiceListOut,
    InvoiceOut,
    InvoiceStatusUpdate,
    InvoiceUpdate,
    PaymentCreate,
    PaymentListOut,
    PaymentOut,
)

router = APIRouter()


@router.get("/invoices", response_model=InvoiceListOut)
def list_invoices(
    customer_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:read")),
) -> InvoiceListOut:
    repo = InvoiceRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        customer_id=customer_id,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return InvoiceListOut(items=[InvoiceOut.model_validate(i) for i in items], next_cursor=None)


@router.post("/invoices", response_model=InvoiceOut)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:write")),
) -> InvoiceOut:
    uc = CreateInvoiceUseCase(db)
    try:
        invoice = uc.execute(
            CreateInvoiceInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                order_id=payload.order_id,
                due_date=payload.due_date,
                notes=payload.notes,
            )
        )
    except (OrderNotInvoiceableError, InvoiceAlreadyExistsError) as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(invoice)
    return InvoiceOut.model_validate(invoice)


@router.get("/invoices/by-order/{order_id}", response_model=InvoiceOut)
def get_invoice_for_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:read")),
) -> InvoiceOut:
    invoice = InvoiceRepository(db).get_for_order(company_id=current_user.active_company_id, order_id=order_id)
    if invoice is None:
        raise NotFoundError("No invoice for this order")
    return InvoiceOut.model_validate(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:read")),
) -> InvoiceOut:
    invoice = InvoiceRepository(db).get(company_id=current_user.active_company_id, invoice_id=invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice not found")
    return InvoiceOut.model_validate(invoice)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:write")),
) -> InvoiceOut:
    uc = UpdateInvoiceUseCase(db)
    try:
        invoice = uc.execute(
            UpdateInvoiceInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                invoice_id=invoice_id,
                due_date=payload.due_date,
                notes=payload.notes,
            )
        )
    except InvoiceImmutableError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(invoice)
    return InvoiceOut.model_validate(invoice)


@router.post("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: uuid.UUID,
    payload: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:write")),
) -> InvoiceOut:
    uc = UpdateInvoiceStatusUseCase(db)
    try:
        invoice = uc.execute(
            UpdateInvoiceStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                invoice_id=invoice_id,
                status=payload.status,
                cancelled_reason=payload.cancelled_reason,
            )
        )
    except InvalidInvoiceTransitionError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(invoice)
    return InvoiceOut.model_validate(invoice)


@router.get("/invoices/{invoice_id}/lines", response_model=InvoiceLineListOut)
def list_invoice_lines(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:read")),
) -> InvoiceLineListOut:
    lines = InvoiceLineRepository(db).list_for_invoice(
        company_id=current_user.active_company_id, invoice_id=invoice_id
    )
    return InvoiceLineListOut(items=[InvoiceLineOut.model_validate(l) for l in lines])


@router.get("/invoices/{invoice_id}/payments", response_model=PaymentListOut)
def list_invoice_payments(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:invoices:read")),
) -> PaymentListOut:
    payments = PaymentRepository(db).list_for_invoice(
        company_id=current_user.active_company_id, invoice_id=invoice_id
    )
    return PaymentListOut(items=[PaymentOut.model_validate(p) for p in payments])


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentOut)
def record_payment(
    invoice_id: uuid.UUID,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:payments:write")),
) -> PaymentOut:
    uc = RecordPaymentUseCase(db)
    try:
        payment = uc.execute(
            RecordPaymentInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                invoice_id=invoice_id,
                amount=payload.amount,
                method=payload.method,
                paid_at=payload.paid_at,
                reference_note=payload.reference_note,
            )
        )
    except (InvoiceImmutableError, OverpaymentError, InvalidPaymentAmountError) as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(payment)
    return PaymentOut.model_validate(payment)
