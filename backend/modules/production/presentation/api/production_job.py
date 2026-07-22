"""The enriched "Production Job" view (requirement #3: customer, project,
reserved slabs, material, thickness, finish, priority, due date, assigned
operator, current stage) plus the production timeline (#5) and the
tracking mutations (priority/operator/stage/due-date) that don't belong on
the coarse status-transition endpoint in work_orders.py."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.crm.infrastructure.repositories.customer_repository import CustomerRepository
from modules.orders.infrastructure.repositories.order_repository import OrderRepository
from modules.production.application.dtos import (
    AssignWorkOrderOperatorInput,
    UpdateWorkOrderInput,
    UpdateWorkOrderPriorityInput,
    UpdateWorkOrderStageInput,
)
from modules.production.application.use_cases.work_order_tracking_use_cases import (
    AssignWorkOrderOperatorUseCase,
    UpdateWorkOrderPriorityUseCase,
    UpdateWorkOrderStageUseCase,
    UpdateWorkOrderUseCase,
)
from modules.production.domain.exceptions import InvalidPriorityError, OperatorNotInCompanyError, StageNotFoundError
from modules.production.infrastructure.repositories.production_stage_repository import ProductionStageRepository
from modules.production.infrastructure.repositories.work_order_event_repository import WorkOrderEventRepository
from modules.production.infrastructure.repositories.work_order_item_repository import WorkOrderItemRepository
from modules.production.infrastructure.repositories.work_order_repository import WorkOrderRepository
from modules.production.presentation.schemas.work_order import (
    EntityRef,
    ProductionJobItemOut,
    ProductionJobOut,
    StageRef,
    WorkOrderEventOut,
    WorkOrderOperatorAssign,
    WorkOrderOut,
    WorkOrderPriorityUpdate,
    WorkOrderStageAssign,
    WorkOrderTimelineOut,
    WorkOrderUpdate,
)
from modules.sales.infrastructure.repositories.project_repository import ProjectRepository

router = APIRouter()

_TRACKING_BUSINESS_ERRORS = (InvalidPriorityError, OperatorNotInCompanyError, StageNotFoundError)


@router.get("/{work_order_id}/job", response_model=ProductionJobOut)
def get_production_job(
    work_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:read")),
) -> ProductionJobOut:
    company_id = current_user.active_company_id
    work_order = WorkOrderRepository(db).get(company_id=company_id, work_order_id=work_order_id)
    if work_order is None:
        raise NotFoundError("Work order not found")

    order = OrderRepository(db).get(company_id=company_id, order_id=uuid.UUID(str(work_order.order_id)))
    if order is None:
        raise NotFoundError("Order not found")

    customer_model = CustomerRepository(db).get_model(company_id=company_id, customer_id=uuid.UUID(str(order.customer_id)))
    project = ProjectRepository(db).get(company_id=company_id, project_id=uuid.UUID(str(order.project_id)))

    stage = None
    if work_order.current_stage_id is not None:
        stage = ProductionStageRepository(db).get(
            company_id=company_id, stage_id=uuid.UUID(str(work_order.current_stage_id))
        )

    rows = WorkOrderItemRepository(db).list_with_material_details(company_id=company_id, work_order_id=work_order.id)
    items = [
        ProductionJobItemOut(
            id=woi.id,
            order_item_id=woi.order_item_id,
            slab_id=woi.slab_id,
            slab_number=slab.slab_number,
            description=order_item.description,
            quantity=order_item.quantity,
            unit=order_item.unit,
            area_m2=slab.area_m2,
            material_id=material.id,
            material_name=material.name,
            thickness_mm=material.thickness_mm,
            finish=material.finish,
        )
        for woi, order_item, slab, material in rows
    ]

    return ProductionJobOut(
        id=work_order.id,
        work_order_number=work_order.work_order_number,
        status=work_order.status,
        priority=work_order.priority,
        due_date=work_order.scheduled_completion_date,
        assigned_operator=work_order.assigned_to,
        current_stage=StageRef(id=stage.id, name=stage.name) if stage else None,
        order=EntityRef(id=order.id, name=order.order_number),
        customer=EntityRef(id=order.customer_id, name=customer_model.name if customer_model else "—"),
        project=EntityRef(id=order.project_id, name=project.name if project else "—"),
        items=items,
        notes=work_order.notes,
        created_at=work_order.created_at,
        completed_at=work_order.completed_at,
        cancelled_at=work_order.cancelled_at,
        cancelled_reason=work_order.cancelled_reason,
    )


@router.get("/{work_order_id}/timeline", response_model=WorkOrderTimelineOut)
def get_work_order_timeline(
    work_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:read")),
) -> WorkOrderTimelineOut:
    events = WorkOrderEventRepository(db).list_for_work_order(
        company_id=current_user.active_company_id, work_order_id=work_order_id
    )
    return WorkOrderTimelineOut(items=[WorkOrderEventOut.model_validate(e) for e in events])


@router.patch("/{work_order_id}", response_model=WorkOrderOut)
def update_work_order(
    work_order_id: uuid.UUID,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> WorkOrderOut:
    work_order = UpdateWorkOrderUseCase(db).execute(
        UpdateWorkOrderInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            work_order_id=work_order_id,
            due_date=payload.due_date,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(work_order)
    return WorkOrderOut.model_validate(work_order)


@router.post("/{work_order_id}/priority", response_model=WorkOrderOut)
def update_work_order_priority(
    work_order_id: uuid.UUID,
    payload: WorkOrderPriorityUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> WorkOrderOut:
    try:
        work_order = UpdateWorkOrderPriorityUseCase(db).execute(
            UpdateWorkOrderPriorityInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                work_order_id=work_order_id,
                priority=payload.priority,
            )
        )
    except _TRACKING_BUSINESS_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(work_order)
    return WorkOrderOut.model_validate(work_order)


@router.post("/{work_order_id}/assign", response_model=WorkOrderOut)
def assign_work_order_operator(
    work_order_id: uuid.UUID,
    payload: WorkOrderOperatorAssign,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> WorkOrderOut:
    try:
        work_order = AssignWorkOrderOperatorUseCase(db).execute(
            AssignWorkOrderOperatorInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                work_order_id=work_order_id,
                operator_user_id=payload.operator_user_id,
            )
        )
    except _TRACKING_BUSINESS_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(work_order)
    return WorkOrderOut.model_validate(work_order)


@router.post("/{work_order_id}/stage", response_model=WorkOrderOut)
def update_work_order_stage(
    work_order_id: uuid.UUID,
    payload: WorkOrderStageAssign,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> WorkOrderOut:
    try:
        work_order = UpdateWorkOrderStageUseCase(db).execute(
            UpdateWorkOrderStageInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                work_order_id=work_order_id,
                stage_id=payload.stage_id,
            )
        )
    except _TRACKING_BUSINESS_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(work_order)
    return WorkOrderOut.model_validate(work_order)
