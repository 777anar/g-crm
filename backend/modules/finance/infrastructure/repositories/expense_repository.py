import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.finance.infrastructure.models.expense import Expense


class ExpenseRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, expense: Expense) -> Expense:
        self.db.add(expense)
        self.db.flush()
        return expense

    def get(self, *, company_id: uuid.UUID, expense_id: uuid.UUID) -> Optional[Expense]:
        return self.db.scalar(
            select(Expense).where(Expense.id == expense_id, Expense.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        order_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Expense]:
        stmt = select(Expense).where(Expense.company_id == company_id)
        if order_id:
            stmt = stmt.where(Expense.order_id == order_id)
        if category:
            stmt = stmt.where(Expense.category == category)
        if date_from:
            stmt = stmt.where(Expense.expense_date >= date_from)
        if date_to:
            stmt = stmt.where(Expense.expense_date <= date_to)
        stmt = stmt.order_by(Expense.expense_date.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
