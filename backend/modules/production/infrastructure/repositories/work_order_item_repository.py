import uuid
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.slab import Slab
from modules.orders.infrastructure.models.order_item import OrderItem
from modules.production.infrastructure.models.work_order_item import WorkOrderItem


class WorkOrderItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, item: WorkOrderItem) -> WorkOrderItem:
        self.db.add(item)
        self.db.flush()
        return item

    def list_for_work_order(self, *, company_id: uuid.UUID, work_order_id: uuid.UUID) -> List[WorkOrderItem]:
        stmt = select(WorkOrderItem).where(
            WorkOrderItem.company_id == company_id, WorkOrderItem.work_order_id == work_order_id
        )
        return list(self.db.scalars(stmt).all())

    def list_with_details(
        self, *, company_id: uuid.UUID, work_order_id: uuid.UUID
    ) -> List[Tuple[WorkOrderItem, OrderItem, Slab]]:
        """Joined view for display -- description/quantity from the Order
        item, slab_number/area from the Slab."""
        stmt = (
            select(WorkOrderItem, OrderItem, Slab)
            .join(OrderItem, OrderItem.id == WorkOrderItem.order_item_id)
            .join(Slab, Slab.id == WorkOrderItem.slab_id)
            .where(WorkOrderItem.company_id == company_id, WorkOrderItem.work_order_id == work_order_id)
        )
        return list(self.db.execute(stmt).all())
