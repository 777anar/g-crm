import uuid

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from modules.sales.application.dtos import AddProjectItemPhotoInput
from modules.sales.infrastructure.models.project_item_photo import ProjectItemPhoto
from modules.sales.infrastructure.repositories.project_item_photo_repository import ProjectItemPhotoRepository
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository

MODULE = "sales"


class AddProjectItemPhotoUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.items = ProjectItemRepository(db)
        self.photos = ProjectItemPhotoRepository(db)

    def execute(self, data: AddProjectItemPhotoInput) -> ProjectItemPhoto:
        if self.items.get(company_id=data.company_id, item_id=data.project_item_id) is None:
            raise NotFoundError("Project item not found")

        photo = ProjectItemPhoto(
            company_id=data.company_id,
            project_item_id=data.project_item_id,
            document_id=data.document_id,
            caption=data.caption,
            sort_order=data.sort_order,
            uploaded_by=data.actor_user_id,
        )
        self.photos.add(photo)

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="project_item.photo_added", entity_type="project_item", entity_id=data.project_item_id,
            diff={"photo_id": str(photo.id)},
        )
        self.db.flush()
        return photo


class DeleteProjectItemPhotoUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.photos = ProjectItemPhotoRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, photo_id: uuid.UUID) -> None:
        photo = self.photos.get(company_id=company_id, photo_id=photo_id)
        if photo is None:
            raise NotFoundError("Photo not found")
        self.photos.delete(photo)

        record_audit(
            self.db, company_id=company_id, module=MODULE, actor_user_id=actor_user_id,
            action="project_item.photo_deleted", entity_type="project_item", entity_id=photo.project_item_id,
            diff={"photo_id": str(photo_id)},
        )
        self.db.flush()
