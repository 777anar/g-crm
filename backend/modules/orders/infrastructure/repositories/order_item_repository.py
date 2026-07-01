import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.orders.infrastructure.models.order_item import OrderItem


class OrderItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, item: OrderItem) -> OrderItem:
        self.db.add(item)
        self.db.flush()
        return item

    def get(self, *, company_id: uuid.UUID, item_id: uuid.UUID) -> Optional[OrderItem]:
        return self.db.scalar(
            select(OrderItem).where(
                OrderItem.id == item_id,
                OrderItem.company_id == company_id,
            )
        )

    def list_for_order(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> List[OrderItem]:
        stmt = (
            select(OrderItem)
            .where(OrderItem.company_id == company_id, OrderItem.order_id == order_id)
            .order_by(OrderItem.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_section(self, *, company_id: uuid.UUID, section_id: uuid.UUID) -> List[OrderItem]:
        stmt = (
            select(OrderItem)
            .where(OrderItem.company_id == company_id, OrderItem.section_id == section_id)
            .order_by(OrderItem.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())

    def update(self, item: OrderItem) -> OrderItem:
        self.db.flush()
        return item
