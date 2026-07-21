import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.marketing.infrastructure.models.campaign import Campaign

_SORTABLE = {
    "name": Campaign.name,
    "status": Campaign.status,
    "created_at": Campaign.created_at,
    "start_date": Campaign.start_date,
}


class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, campaign: Campaign) -> Campaign:
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def get(self, *, company_id: uuid.UUID, campaign_id: uuid.UUID) -> Optional[Campaign]:
        return self.db.scalar(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Campaign]:
        stmt = select(Campaign).where(Campaign.company_id == company_id)
        if status:
            stmt = stmt.where(Campaign.status == status)
        if channel:
            stmt = stmt.where(Campaign.channel == channel)
        if search:
            stmt = stmt.where(Campaign.name.ilike(f"%{search.strip()}%"))
        sort_col = _SORTABLE.get((sort or "-created_at").lstrip("-"), Campaign.created_at)
        desc = not sort or sort.startswith("-")
        stmt = stmt.order_by(sort_col.desc() if desc else sort_col.asc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
