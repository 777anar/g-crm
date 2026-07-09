import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import AddProjectItemPhotoInput
from modules.sales.application.use_cases import AddProjectItemPhotoUseCase, DeleteProjectItemPhotoUseCase
from modules.sales.infrastructure.repositories.project_item_photo_repository import ProjectItemPhotoRepository
from modules.sales.presentation.schemas.project_item_photo import (
    ProjectItemPhotoCreate,
    ProjectItemPhotoListOut,
    ProjectItemPhotoOut,
)

router = APIRouter()


@router.get("/project-items/{item_id}/photos", response_model=ProjectItemPhotoListOut)
def list_photos(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectItemPhotoListOut:
    items = ProjectItemPhotoRepository(db).list_for_item(
        company_id=current_user.active_company_id, project_item_id=item_id
    )
    return ProjectItemPhotoListOut(items=[ProjectItemPhotoOut.model_validate(p) for p in items])


@router.post("/project-items/{item_id}/photos", response_model=ProjectItemPhotoOut)
def add_photo(
    item_id: uuid.UUID,
    payload: ProjectItemPhotoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemPhotoOut:
    uc = AddProjectItemPhotoUseCase(db)
    photo = uc.execute(
        AddProjectItemPhotoInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_item_id=item_id,
            document_id=payload.document_id,
            caption=payload.caption,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(photo)
    return ProjectItemPhotoOut.model_validate(photo)


@router.delete("/project-item-photos/{photo_id}", status_code=204)
def delete_photo(
    photo_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> None:
    uc = DeleteProjectItemPhotoUseCase(db)
    uc.execute(company_id=current_user.active_company_id, actor_user_id=current_user.user_id, photo_id=photo_id)
    db.commit()
