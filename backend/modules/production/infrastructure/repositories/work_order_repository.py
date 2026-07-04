import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.production.infrastructure.models.work_order import WorkOrder
from modules.production.infrastructure.models.work_order_number_sequence import WorkOrderNumberSequence


class WorkOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, work_order: WorkOrder) -> WorkOrder:
        self.db.add(work_order)
        self.db.flush()
        return work_order

    def get(self, *, company_id: uuid.UUID, work_order_id: uuid.UUID) -> Optional[WorkOrder]:
        return self.db.scalar(
            select(WorkOrder).where(WorkOrder.id == work_order_id, WorkOrder.company_id == company_id)
        )

    def get_for_order(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> Optional[WorkOrder]:
        return self.db.scalar(
            select(WorkOrder).where(WorkOrder.order_id == order_id, WorkOrder.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[WorkOrder]:
        stmt = select(WorkOrder).where(WorkOrder.company_id == company_id)
        if status:
            stmt = stmt.where(WorkOrder.status == status)
        if search:
            stmt = stmt.where(WorkOrder.work_order_number.ilike(f"%{search}%"))
        stmt = stmt.order_by(WorkOrder.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def next_work_order_number(self, *, company_id: uuid.UUID, year: int) -> str:
        """Atomically increments the per-company-per-year counter and returns
        a formatted work order number like 'WO-2026-0001'."""
        seq = self.db.scalar(
            select(WorkOrderNumberSequence).where(
                WorkOrderNumberSequence.company_id == company_id,
                WorkOrderNumberSequence.year == year,
            )
        )
        if seq is None:
            seq = WorkOrderNumberSequence(company_id=company_id, year=year, last_number=0)
            self.db.add(seq)
            self.db.flush()
        seq.last_number += 1
        self.db.flush()
        return f"WO-{year}-{seq.last_number:04d}"
