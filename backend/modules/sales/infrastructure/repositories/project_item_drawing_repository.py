import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.project_item_drawing import ProjectItemDrawing


class ProjectItemDrawingRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, drawing: ProjectItemDrawing) -> ProjectItemDrawing:
        self.db.add(drawing)
        self.db.flush()
        return drawing

    def get(self, *, company_id: uuid.UUID, drawing_id: uuid.UUID) -> Optional[ProjectItemDrawing]:
        return self.db.scalar(
            select(ProjectItemDrawing).where(
                ProjectItemDrawing.id == drawing_id, ProjectItemDrawing.company_id == company_id
            )
        )

    def list_for_item(self, *, company_id: uuid.UUID, project_item_id: uuid.UUID) -> List[ProjectItemDrawing]:
        stmt = (
            select(ProjectItemDrawing)
            .where(
                ProjectItemDrawing.company_id == company_id,
                ProjectItemDrawing.project_item_id == project_item_id,
            )
            .order_by(ProjectItemDrawing.sort_order.asc(), ProjectItemDrawing.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, drawing: ProjectItemDrawing) -> None:
        self.db.delete(drawing)
        self.db.flush()
