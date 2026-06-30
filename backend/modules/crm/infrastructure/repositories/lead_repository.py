import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.crm.infrastructure.models.lead import Lead


class LeadRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, lead: Lead) -> Lead:
        self.db.add(lead)
        self.db.flush()
        return lead

    def get(self, *, company_id: uuid.UUID, lead_id: uuid.UUID) -> Optional[Lead]:
        return self.db.scalar(select(Lead).where(Lead.id == lead_id, Lead.company_id == company_id))

    def list(
        self,
        *,
        company_id: uuid.UUID,
        status: Optional[str] = None,
        source_channel: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Lead]:
        stmt = select(Lead).where(Lead.company_id == company_id)
        if status:
            stmt = stmt.where(Lead.status == status)
        if source_channel:
            stmt = stmt.where(Lead.source_channel == source_channel)
        stmt = stmt.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
