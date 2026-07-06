import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError, ValidationAPIError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.crm.application.dtos import (
    CreateTaskInput,
    DeleteTaskInput,
    UpdateTaskInput,
    UpdateTaskStatusInput,
)
from modules.crm.application.use_cases import (
    CreateTaskUseCase,
    DeleteTaskUseCase,
    UpdateTaskStatusUseCase,
    UpdateTaskUseCase,
)
from modules.crm.domain.exceptions import (
    InvalidRecurrenceError,
    InvalidTaskTransitionError,
    TaskImmutableError,
)
from modules.crm.infrastructure.repositories.task_repository import TaskRepository
from modules.crm.presentation.schemas.task import (
    TaskCreate,
    TaskListOut,
    TaskOut,
    TaskStatusUpdate,
    TaskUpdate,
)

router = APIRouter()


@router.get("/tasks", response_model=TaskListOut)
def list_tasks(
    assigned_to: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    related_entity_type: Optional[str] = Query(default=None),
    related_entity_id: Optional[uuid.UUID] = Query(default=None),
    due_before: Optional[datetime] = Query(default=None),
    due_after: Optional[datetime] = Query(default=None),
    exclude_terminal: bool = Query(default=False),
    search: Optional[str] = Query(default=None, description="Matches title or description"),
    sort: Optional[str] = Query(default=None, description="One of title, due_date, priority, status, created_at, updated_at; prefix with - for descending"),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:read")),
) -> TaskListOut:
    repo = TaskRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        assigned_to=assigned_to,
        status=status,
        priority=priority,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        due_before=due_before,
        due_after=due_after,
        exclude_terminal=exclude_terminal,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return TaskListOut(items=[TaskOut.model_validate(t) for t in page], next_cursor=next_cursor)


@router.post("/tasks", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:write")),
) -> TaskOut:
    use_case = CreateTaskUseCase(db)
    try:
        task = use_case.execute(
            CreateTaskInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                title=payload.title,
                description=payload.description,
                priority=payload.priority,
                due_date=payload.due_date,
                remind_at=payload.remind_at,
                assigned_to=payload.assigned_to,
                tags=payload.tags,
                related_entity_type=payload.related_entity_type,
                related_entity_id=payload.related_entity_id,
                is_recurring=payload.is_recurring,
                recurrence_rule=payload.recurrence_rule,
                recurrence_interval=payload.recurrence_interval,
                recurrence_end_date=payload.recurrence_end_date,
            )
        )
    except InvalidRecurrenceError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:read")),
) -> TaskOut:
    task = TaskRepository(db).get(company_id=current_user.active_company_id, task_id=task_id)
    if task is None:
        raise NotFoundError("Task not found")
    return TaskOut.model_validate(task)


@router.get("/tasks/{task_id}/series", response_model=TaskListOut)
def list_task_series(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:read")),
) -> TaskListOut:
    task = TaskRepository(db).get(company_id=current_user.active_company_id, task_id=task_id)
    if task is None:
        raise NotFoundError("Task not found")
    series_root_id = task.series_id or task.id
    items = TaskRepository(db).list_for_series(company_id=current_user.active_company_id, series_id=series_root_id)
    return TaskListOut(items=[TaskOut.model_validate(t) for t in items])


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:write")),
) -> TaskOut:
    use_case = UpdateTaskUseCase(db)
    try:
        task = use_case.execute(
            UpdateTaskInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                task_id=task_id,
                title=payload.title,
                description=payload.description,
                priority=payload.priority,
                due_date=payload.due_date,
                remind_at=payload.remind_at,
                assigned_to=payload.assigned_to,
                tags=payload.tags,
                related_entity_type=payload.related_entity_type,
                related_entity_id=payload.related_entity_id,
                is_recurring=payload.is_recurring,
                recurrence_rule=payload.recurrence_rule,
                recurrence_interval=payload.recurrence_interval,
                recurrence_end_date=payload.recurrence_end_date,
            )
        )
    except TaskImmutableError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    except InvalidRecurrenceError as exc:
        raise ValidationAPIError(str(exc)) from exc
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.post("/tasks/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: uuid.UUID,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:write")),
) -> TaskOut:
    use_case = UpdateTaskStatusUseCase(db)
    try:
        task = use_case.execute(
            UpdateTaskStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                task_id=task_id,
                status=payload.status,
                cancelled_reason=payload.cancelled_reason,
            )
        )
    except InvalidTaskTransitionError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("crm:tasks:write")),
) -> None:
    use_case = DeleteTaskUseCase(db)
    use_case.execute(
        DeleteTaskInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            task_id=task_id,
        )
    )
    db.commit()
