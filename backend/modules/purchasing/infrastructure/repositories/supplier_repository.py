import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.purchasing.infrastructure.models.supplier import Supplier


class SupplierRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, supplier: Supplier) -> Supplier:
        self.db.add(supplier)
        self.db.flush()
        return supplier

    def get(self, *, company_id: uuid.UUID, supplier_id: uuid.UUID) -> Optional[Supplier]:
        return self.db.scalar(
            select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        include_hidden: bool = False,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Supplier]:
        stmt = select(Supplier).where(Supplier.company_id == company_id)
        if not include_hidden:
            stmt = stmt.where(Supplier.status == "active")
        if search:
            stmt = stmt.where(Supplier.name.ilike(f"%{search.strip()}%"))
        stmt = stmt.order_by(Supplier.name.asc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
