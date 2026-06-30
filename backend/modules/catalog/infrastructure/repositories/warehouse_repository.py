import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.warehouse import Warehouse


class WarehouseRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, warehouse: Warehouse) -> Warehouse:
        self.db.add(warehouse)
        self.db.flush()
        return warehouse

    def get(self, *, company_id: uuid.UUID, warehouse_id: uuid.UUID) -> Optional[Warehouse]:
        return self.db.scalar(
            select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.company_id == company_id)
        )

    def list(self, *, company_id: uuid.UUID, include_hidden: bool = False) -> List[Warehouse]:
        stmt = select(Warehouse).where(Warehouse.company_id == company_id)
        if not include_hidden:
            stmt = stmt.where(Warehouse.status == "active")
        stmt = stmt.order_by(Warehouse.name.asc())
        return list(self.db.scalars(stmt).all())
