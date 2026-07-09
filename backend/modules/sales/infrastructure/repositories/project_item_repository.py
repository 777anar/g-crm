import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.project_item import ProjectItem


class ProjectItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, item: ProjectItem) -> ProjectItem:
        self.db.add(item)
        self.db.flush()
        return item

    def get(self, *, company_id: uuid.UUID, item_id: uuid.UUID) -> Optional[ProjectItem]:
        return self.db.scalar(
            select(ProjectItem).where(ProjectItem.id == item_id, ProjectItem.company_id == company_id)
        )

    def list_for_room(self, *, company_id: uuid.UUID, room_id: uuid.UUID) -> List[ProjectItem]:
        stmt = (
            select(ProjectItem)
            .where(ProjectItem.company_id == company_id, ProjectItem.room_id == room_id)
            .order_by(ProjectItem.sort_order.asc(), ProjectItem.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_project(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> List[ProjectItem]:
        stmt = (
            select(ProjectItem)
            .where(ProjectItem.company_id == company_id, ProjectItem.project_id == project_id)
            .order_by(ProjectItem.sort_order.asc(), ProjectItem.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, item: ProjectItem) -> None:
        self.db.delete(item)
        self.db.flush()
