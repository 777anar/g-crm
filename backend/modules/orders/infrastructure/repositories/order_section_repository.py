import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.orders.infrastructure.models.order_section import OrderSection


class OrderSectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, section: OrderSection) -> OrderSection:
        self.db.add(section)
        self.db.flush()
        return section

    def get(self, *, company_id: uuid.UUID, section_id: uuid.UUID) -> Optional[OrderSection]:
        return self.db.scalar(
            select(OrderSection).where(
                OrderSection.id == section_id,
                OrderSection.company_id == company_id,
            )
        )

    def list_for_order(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> List[OrderSection]:
        stmt = (
            select(OrderSection)
            .where(OrderSection.company_id == company_id, OrderSection.order_id == order_id)
            .order_by(OrderSection.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())
