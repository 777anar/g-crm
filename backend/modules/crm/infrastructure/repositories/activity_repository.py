import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.crm.infrastructure.models.activity import Activity


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, activity: Activity) -> Activity:
        self.db.add(activity)
        self.db.flush()
        return activity

    def list_for_entity(
        self,
        *,
        company_id: uuid.UUID,
        related_entity_type: str,
        related_entity_id: uuid.UUID,
        type_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Activity]:
        stmt = select(Activity).where(
            Activity.company_id == company_id,
            Activity.related_entity_type == related_entity_type,
            Activity.related_entity_id == related_entity_id,
        )
        if type_filter:
            stmt = stmt.where(Activity.type == type_filter)
        stmt = stmt.order_by(Activity.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
