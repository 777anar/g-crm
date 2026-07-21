import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.purchasing.infrastructure.models.goods_receipt import GoodsReceipt


class GoodsReceiptRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, receipt: GoodsReceipt) -> GoodsReceipt:
        self.db.add(receipt)
        self.db.flush()
        return receipt

    def list_for_order(self, *, company_id: uuid.UUID, purchase_order_id: uuid.UUID) -> List[GoodsReceipt]:
        stmt = (
            select(GoodsReceipt)
            .where(GoodsReceipt.company_id == company_id, GoodsReceipt.purchase_order_id == purchase_order_id)
            .order_by(GoodsReceipt.received_at.desc())
        )
        return list(self.db.scalars(stmt).all())
