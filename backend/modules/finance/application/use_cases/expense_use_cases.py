"""Expense use cases: a simple company-wide or Order-linked cost entry, with
no lifecycle of its own (unlike Invoice/Payment) -- created once, listed, done."""
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.finance.application.dtos import CreateExpenseInput
from modules.finance.domain import events as finance_events
from modules.finance.domain.exceptions import InvalidExpenseAmountError
from modules.finance.infrastructure.models.expense import Expense
from modules.finance.infrastructure.repositories.expense_repository import ExpenseRepository
from modules.orders.infrastructure.repositories.order_repository import OrderRepository

MODULE = "finance"


class CreateExpenseUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.expenses = ExpenseRepository(db)
        self.orders = OrderRepository(db)

    def execute(self, data: CreateExpenseInput) -> Expense:
        if data.amount <= 0:
            raise InvalidExpenseAmountError("Expense amount must be positive")

        if data.order_id is not None:
            order = self.orders.get(company_id=data.company_id, order_id=data.order_id)
            if order is None:
                raise NotFoundError("Order not found")

        expense = Expense(
            company_id=data.company_id,
            order_id=data.order_id,
            category=data.category,
            description=data.description,
            amount=data.amount,
            currency=data.currency,
            expense_date=data.expense_date,
            created_by=data.actor_user_id,
        )
        self.expenses.add(expense)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="expense.created",
            entity_type="expense",
            entity_id=expense.id,
            diff={"category": data.category, "amount": str(data.amount), "order_id": str(data.order_id) if data.order_id else None},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=finance_events.EXPENSE_CREATED,
                company_id=data.company_id,
                payload={
                    "expense_id": str(expense.id),
                    "category": data.category,
                    "amount": str(data.amount),
                    "order_id": str(data.order_id) if data.order_id else None,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return expense
