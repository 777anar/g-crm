import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.purchasing.infrastructure.models.purchase_order import PurchaseOrder
from modules.purchasing.infrastructure.models.purchase_order_number_sequence import PurchaseOrderNumberSequence

_SORTABLE = {
    "po_number": PurchaseOrder.po_number,
    "status": PurchaseOrder.status,
    "created_at": PurchaseOrder.created_at,
    "total_amount": PurchaseOrder.total_amount,
    "expected_delivery_date": PurchaseOrder.expected_delivery_date,
}


class PurchaseOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, purchase_order: PurchaseOrder) -> PurchaseOrder:
        self.db.add(purchase_order)
        self.db.flush()
        return purchase_order

    def get(self, *, company_id: uuid.UUID, purchase_order_id: uuid.UUID) -> Optional[PurchaseOrder]:
        return self.db.scalar(
            select(PurchaseOrder).where(
                PurchaseOrder.id == purchase_order_id, PurchaseOrder.company_id == company_id
            )
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[PurchaseOrder]:
        stmt = select(PurchaseOrder).where(PurchaseOrder.company_id == company_id)
        if supplier_id:
            stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        if search:
            stmt = stmt.where(PurchaseOrder.po_number.ilike(f"%{search.strip()}%"))
        sort_col = _SORTABLE.get((sort or "-created_at").lstrip("-"), PurchaseOrder.created_at)
        desc = not sort or sort.startswith("-")
        stmt = stmt.order_by(sort_col.desc() if desc else sort_col.asc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def next_po_number(self, *, company_id: uuid.UUID, year: int) -> str:
        """Atomically increments the per-company-per-year counter and returns
        a formatted purchase order number like 'PO-2026-0001'."""
        seq = self.db.scalar(
            select(PurchaseOrderNumberSequence).where(
                PurchaseOrderNumberSequence.company_id == company_id,
                PurchaseOrderNumberSequence.year == year,
            )
        )
        if seq is None:
            seq = PurchaseOrderNumberSequence(company_id=company_id, year=year, last_number=0)
            self.db.add(seq)
            self.db.flush()
        seq.last_number += 1
        self.db.flush()
        return f"PO-{year}-{seq.last_number:04d}"
