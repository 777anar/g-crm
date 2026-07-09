import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.project_item_photo import ProjectItemPhoto


class ProjectItemPhotoRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, photo: ProjectItemPhoto) -> ProjectItemPhoto:
        self.db.add(photo)
        self.db.flush()
        return photo

    def get(self, *, company_id: uuid.UUID, photo_id: uuid.UUID) -> Optional[ProjectItemPhoto]:
        return self.db.scalar(
            select(ProjectItemPhoto).where(
                ProjectItemPhoto.id == photo_id, ProjectItemPhoto.company_id == company_id
            )
        )

    def list_for_item(self, *, company_id: uuid.UUID, project_item_id: uuid.UUID) -> List[ProjectItemPhoto]:
        stmt = (
            select(ProjectItemPhoto)
            .where(
                ProjectItemPhoto.company_id == company_id,
                ProjectItemPhoto.project_item_id == project_item_id,
            )
            .order_by(ProjectItemPhoto.sort_order.asc(), ProjectItemPhoto.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, photo: ProjectItemPhoto) -> None:
        self.db.delete(photo)
        self.db.flush()
