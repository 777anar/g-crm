import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import CreateProjectItemInput, UpdateProjectItemInput
from modules.sales.application.use_cases import (
    CreateProjectItemUseCase,
    DeleteProjectItemUseCase,
    UpdateProjectItemUseCase,
)
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository
from modules.sales.presentation.schemas.project_item import (
    ProjectItemCreate,
    ProjectItemListOut,
    ProjectItemOut,
    ProjectItemUpdate,
)

router = APIRouter()


@router.get("/rooms/{room_id}/items", response_model=ProjectItemListOut)
def list_project_items(
    room_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectItemListOut:
    items = ProjectItemRepository(db).list_for_room(company_id=current_user.active_company_id, room_id=room_id)
    return ProjectItemListOut(items=[ProjectItemOut.model_validate(i) for i in items])


@router.get("/projects/{project_id}/items", response_model=ProjectItemListOut)
def list_project_items_for_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectItemListOut:
    items = ProjectItemRepository(db).list_for_project(company_id=current_user.active_company_id, project_id=project_id)
    return ProjectItemListOut(items=[ProjectItemOut.model_validate(i) for i in items])


@router.post("/rooms/{room_id}/items", response_model=ProjectItemOut)
def create_project_item(
    room_id: uuid.UUID,
    payload: ProjectItemCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemOut:
    uc = CreateProjectItemUseCase(db)
    item = uc.execute(
        CreateProjectItemInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            room_id=room_id,
            item_type=payload.item_type,
            name=payload.name,
            material_id=payload.material_id,
            material_thickness_id=payload.material_thickness_id,
            material_size_id=payload.material_size_id,
            quantity=payload.quantity,
            unit=payload.unit,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    db.refresh(item)
    return ProjectItemOut.model_validate(item)


@router.patch("/project-items/{item_id}", response_model=ProjectItemOut)
def update_project_item(
    item_id: uuid.UUID,
    payload: ProjectItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectItemOut:
    uc = UpdateProjectItemUseCase(db)
    item = uc.execute(
        UpdateProjectItemInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_item_id=item_id,
            item_type=payload.item_type,
            name=payload.name,
            material_id=payload.material_id,
            material_thickness_id=payload.material_thickness_id,
            material_size_id=payload.material_size_id,
            quantity=payload.quantity,
            unit=payload.unit,
            notes=payload.notes,
            sort_order=payload.sort_order,
            production_status=payload.production_status,
            installation_status=payload.installation_status,
        )
    )
    db.commit()
    db.refresh(item)
    return ProjectItemOut.model_validate(item)


@router.delete("/project-items/{item_id}", status_code=204)
def delete_project_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> None:
    uc = DeleteProjectItemUseCase(db)
    uc.execute(company_id=current_user.active_company_id, actor_user_id=current_user.user_id, project_item_id=item_id)
    db.commit()
