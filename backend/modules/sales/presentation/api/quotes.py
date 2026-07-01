import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, ConflictError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import (
    CreateQuoteInput,
    UpdateQuoteInput,
    UpdateQuoteStatusInput,
)
from modules.sales.application.use_cases import (
    CreateQuoteUseCase,
    UpdateQuoteStatusUseCase,
    UpdateQuoteUseCase,
)
from modules.sales.domain.exceptions import InvalidQuoteTransitionError, SlabConflictError
from modules.sales.infrastructure.repositories.quote_repository import QuoteRepository
from modules.sales.presentation.schemas.quote import (
    QuoteCreate,
    QuoteListOut,
    QuoteOut,
    QuoteStatusUpdate,
    QuoteUpdate,
)

router = APIRouter()


@router.get("/projects/{project_id}/quotes", response_model=QuoteListOut)
def list_quotes_for_project(
    project_id: uuid.UUID,
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:read")),
) -> QuoteListOut:
    repo = QuoteRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list_for_project(
        company_id=current_user.active_company_id,
        project_id=project_id,
    )
    return QuoteListOut(
        items=[QuoteOut.model_validate(q) for q in items],
        next_cursor=None,
    )


@router.post("/projects/{project_id}/quotes", response_model=QuoteOut)
def create_quote(
    project_id: uuid.UUID,
    payload: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> QuoteOut:
    uc = CreateQuoteUseCase(db)
    quote = uc.execute(
        CreateQuoteInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_id=project_id,
            currency=payload.currency,
            price_list_id=payload.price_list_id,
            valid_until=payload.valid_until,
            internal_notes=payload.internal_notes,
            customer_notes=payload.customer_notes,
            vat_rate=payload.vat_rate,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
        )
    )
    db.commit()
    db.refresh(quote)
    return QuoteOut.model_validate(quote)


@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:read")),
) -> QuoteOut:
    quote = QuoteRepository(db).get(
        company_id=current_user.active_company_id, quote_id=quote_id
    )
    if quote is None:
        raise NotFoundError("Quote not found")
    return QuoteOut.model_validate(quote)


@router.patch("/quotes/{quote_id}", response_model=QuoteOut)
def update_quote(
    quote_id: uuid.UUID,
    payload: QuoteUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> QuoteOut:
    uc = UpdateQuoteUseCase(db)
    quote = uc.execute(
        UpdateQuoteInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            quote_id=quote_id,
            currency=payload.currency,
            price_list_id=payload.price_list_id,
            valid_until=payload.valid_until,
            internal_notes=payload.internal_notes,
            customer_notes=payload.customer_notes,
            vat_rate=payload.vat_rate,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
        )
    )
    db.commit()
    db.refresh(quote)
    return QuoteOut.model_validate(quote)


@router.post("/quotes/{quote_id}/status", response_model=QuoteOut)
def update_quote_status(
    quote_id: uuid.UUID,
    payload: QuoteStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:quotes:write")),
) -> QuoteOut:
    uc = UpdateQuoteStatusUseCase(db)
    try:
        quote = uc.execute(
            UpdateQuoteStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                quote_id=quote_id,
                status=payload.status,
            )
        )
    except InvalidQuoteTransitionError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    except SlabConflictError as exc:
        raise ConflictError(str(exc)) from exc
    db.commit()
    db.refresh(quote)
    return QuoteOut.model_validate(quote)
