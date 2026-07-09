import uuid

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from modules.sales.application.dtos import AddProjectItemDrawingInput
from modules.sales.infrastructure.models.project_item_drawing import ProjectItemDrawing
from modules.sales.infrastructure.repositories.project_item_drawing_repository import ProjectItemDrawingRepository
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository

MODULE = "sales"


class AddProjectItemDrawingUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.items = ProjectItemRepository(db)
        self.drawings = ProjectItemDrawingRepository(db)

    def execute(self, data: AddProjectItemDrawingInput) -> ProjectItemDrawing:
        if self.items.get(company_id=data.company_id, item_id=data.project_item_id) is None:
            raise NotFoundError("Project item not found")

        drawing = ProjectItemDrawing(
            company_id=data.company_id,
            project_item_id=data.project_item_id,
            document_id=data.document_id,
            drawing_type=data.drawing_type,
            label=data.label,
            sort_order=data.sort_order,
            uploaded_by=data.actor_user_id,
        )
        self.drawings.add(drawing)

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="project_item.drawing_added", entity_type="project_item", entity_id=data.project_item_id,
            diff={"drawing_id": str(drawing.id), "drawing_type": drawing.drawing_type},
        )
        self.db.flush()
        return drawing


class DeleteProjectItemDrawingUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.drawings = ProjectItemDrawingRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, drawing_id: uuid.UUID) -> None:
        drawing = self.drawings.get(company_id=company_id, drawing_id=drawing_id)
        if drawing is None:
            raise NotFoundError("Drawing not found")
        self.drawings.delete(drawing)

        record_audit(
            self.db, company_id=company_id, module=MODULE, actor_user_id=actor_user_id,
            action="project_item.drawing_deleted", entity_type="project_item", entity_id=drawing.project_item_id,
            diff={"drawing_id": str(drawing_id)},
        )
        self.db.flush()
