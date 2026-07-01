import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.orders.infrastructure.models.order import Order
from modules.orders.infrastructure.models.order_number_sequence import OrderNumberSequence


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def get(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> Optional[Order]:
        return self.db.scalar(
            select(Order).where(Order.id == order_id, Order.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Order]:
        stmt = select(Order).where(Order.company_id == company_id)
        if project_id:
            stmt = stmt.where(Order.project_id == project_id)
        if customer_id:
            stmt = stmt.where(Order.customer_id == customer_id)
        if status:
            stmt = stmt.where(Order.status == status)
        if search:
            stmt = stmt.where(Order.order_number.ilike(f"%{search}%"))
        stmt = stmt.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_for_project(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> List[Order]:
        stmt = (
            select(Order)
            .where(Order.company_id == company_id, Order.project_id == project_id)
            .order_by(Order.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def next_order_number(self, *, company_id: uuid.UUID, year: int) -> str:
        """Atomically increments the per-company-per-year counter and returns
        a formatted order number like 'ORD-2026-0001'."""
        seq = self.db.scalar(
            select(OrderNumberSequence).where(
                OrderNumberSequence.company_id == company_id,
                OrderNumberSequence.year == year,
            )
        )
        if seq is None:
            seq = OrderNumberSequence(company_id=company_id, year=year, last_number=0)
            self.db.add(seq)
            self.db.flush()
        seq.last_number += 1
        self.db.flush()
        return f"ORD-{year}-{seq.last_number:04d}"
