import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.purchasing.infrastructure.models.purchase_order_line import PurchaseOrderLine


class PurchaseOrderLineRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, line: PurchaseOrderLine) -> PurchaseOrderLine:
        self.db.add(line)
        self.db.flush()
        return line

    def get(self, *, company_id: uuid.UUID, line_id: uuid.UUID) -> Optional[PurchaseOrderLine]:
        return self.db.scalar(
            select(PurchaseOrderLine).where(
                PurchaseOrderLine.id == line_id, PurchaseOrderLine.company_id == company_id
            )
        )

    def list_for_order(self, *, company_id: uuid.UUID, purchase_order_id: uuid.UUID) -> List[PurchaseOrderLine]:
        stmt = (
            select(PurchaseOrderLine)
            .where(
                PurchaseOrderLine.company_id == company_id,
                PurchaseOrderLine.purchase_order_id == purchase_order_id,
            )
            .order_by(PurchaseOrderLine.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())
