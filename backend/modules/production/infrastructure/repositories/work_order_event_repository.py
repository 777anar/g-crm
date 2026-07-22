import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.production.infrastructure.models.work_order_event import WorkOrderEvent


class WorkOrderEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: WorkOrderEvent) -> WorkOrderEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_for_work_order(self, *, company_id: uuid.UUID, work_order_id: uuid.UUID) -> List[WorkOrderEvent]:
        stmt = (
            select(WorkOrderEvent)
            .where(WorkOrderEvent.company_id == company_id, WorkOrderEvent.work_order_id == work_order_id)
            .order_by(WorkOrderEvent.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
