import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.sales.application.dtos import CreateProjectInput, UpdateProjectInput
from modules.sales.application.use_cases import CreateProjectUseCase, UpdateProjectUseCase
from modules.sales.infrastructure.repositories.project_repository import ProjectRepository
from modules.sales.presentation.schemas.project import (
    ProjectCreate,
    ProjectListOut,
    ProjectOut,
    ProjectUpdate,
)

router = APIRouter()


@router.get("/projects", response_model=ProjectListOut)
def list_projects(
    customer_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectListOut:
    repo = ProjectRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        customer_id=customer_id,
        status=status,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    return ProjectListOut(
        items=[ProjectOut.model_validate(p) for p in page],
        next_cursor=encode_cursor(offset=offset + limit) if has_more else None,
    )


@router.post("/projects", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectOut:
    uc = CreateProjectUseCase(db)
    project = uc.execute(
        CreateProjectInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            customer_id=payload.customer_id,
            name=payload.name,
            project_type=payload.project_type,
            address=payload.address,
            notes=payload.notes,
            assigned_to=payload.assigned_to,
        )
    )
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:read")),
) -> ProjectOut:
    project = ProjectRepository(db).get(
        company_id=current_user.active_company_id, project_id=project_id
    )
    if project is None:
        raise NotFoundError("Project not found")
    return ProjectOut.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("sales:projects:write")),
) -> ProjectOut:
    uc = UpdateProjectUseCase(db)
    project = uc.execute(
        UpdateProjectInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            project_id=project_id,
            name=payload.name,
            project_type=payload.project_type,
            address=payload.address,
            notes=payload.notes,
            assigned_to=payload.assigned_to,
            status=payload.status,
        )
    )
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)
