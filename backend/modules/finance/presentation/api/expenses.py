import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.finance.application.dtos import CreateExpenseInput
from modules.finance.application.use_cases import CreateExpenseUseCase
from modules.finance.domain.exceptions import InvalidExpenseAmountError
from modules.finance.infrastructure.repositories.expense_repository import ExpenseRepository
from modules.finance.presentation.schemas.finance import ExpenseCreate, ExpenseListOut, ExpenseOut

router = APIRouter()


@router.get("/expenses", response_model=ExpenseListOut)
def list_expenses(
    order_id: Optional[uuid.UUID] = Query(default=None),
    category: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:expenses:read")),
) -> ExpenseListOut:
    repo = ExpenseRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        order_id=order_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return ExpenseListOut(items=[ExpenseOut.model_validate(e) for e in items], next_cursor=None)


@router.post("/expenses", response_model=ExpenseOut)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:expenses:write")),
) -> ExpenseOut:
    uc = CreateExpenseUseCase(db)
    try:
        expense = uc.execute(
            CreateExpenseInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                category=payload.category,
                amount=payload.amount,
                expense_date=payload.expense_date,
                order_id=payload.order_id,
                description=payload.description,
                currency=payload.currency,
            )
        )
    except InvalidExpenseAmountError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(expense)
    return ExpenseOut.model_validate(expense)


@router.get("/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("finance:expenses:read")),
) -> ExpenseOut:
    expense = ExpenseRepository(db).get(company_id=current_user.active_company_id, expense_id=expense_id)
    if expense is None:
        raise NotFoundError("Expense not found")
    return ExpenseOut.model_validate(expense)
