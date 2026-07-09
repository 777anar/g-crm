import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import AddProjectItemDrawingInput
from modules.sales.application.use_cases import AddProjectItemDrawingUseCase, DeleteProjectItemDrawingUseCase
from modules.sales.infrastructure.repositories.project_item_drawing_repository import ProjectItemDrawingRepository
from modules.sales.presentation.schemas.project_item_drawing import (
    ProjectItemDrawingCreate,
    ProjectItemDrawingListOut,
    ProjectItemDrawingOut,
)

router = APIRouter()


@router.get("/project-items/{item_id}/drawings", response_model=ProjectItemDrawingListOut)
def list_drawings(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectItemDrawingListOut:
    items = ProjectItemDrawingRepository(db).list_for_item(
        company_id=current_user.active_company_id, project_item_id=item_id
    )
    return ProjectItemDrawingListOut(items=[ProjectItemDrawingOut.model_validate(d) for d in items])


@router.post("/project-items/{item_id}/drawings", response_model=ProjectItemDrawingOut)
def add_drawing(
    item_id: uuid.UUID,
    payload: ProjectItemDrawingCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemDrawingOut:
    uc = AddProjectItemDrawingUseCase(db)
    drawing = uc.execute(
        AddProjectItemDrawingInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_item_id=item_id,
            document_id=payload.document_id,
            drawing_type=payload.drawing_type,
            label=payload.label,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(drawing)
    return ProjectItemDrawingOut.model_validate(drawing)


@router.delete("/project-item-drawings/{drawing_id}", status_code=204)
def delete_drawing(
    drawing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> None:
    uc = DeleteProjectItemDrawingUseCase(db)
    uc.execute(company_id=current_user.active_company_id, actor_user_id=current_user.user_id, drawing_id=drawing_id)
    db.commit()
