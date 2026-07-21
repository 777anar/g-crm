import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.production.application.dtos import CreateWorkOrderInput, UpdateWorkOrderStatusInput
from modules.production.application.use_cases import CreateWorkOrderUseCase, UpdateWorkOrderStatusUseCase
from modules.production.domain.exceptions import (
    InvalidWorkOrderTransitionError,
    NoProductionItemsError,
    OrderNotReadyForProductionError,
    SlabNotReservedError,
    WorkOrderAlreadyExistsError,
)
from modules.production.infrastructure.repositories.work_order_item_repository import WorkOrderItemRepository
from modules.production.infrastructure.repositories.work_order_repository import WorkOrderRepository
from modules.production.presentation.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderItemListOut,
    WorkOrderItemOut,
    WorkOrderListOut,
    WorkOrderOut,
    WorkOrderStatusUpdate,
)

router = APIRouter()

_BUSINESS_RULE_ERRORS = (
    OrderNotReadyForProductionError,
    WorkOrderAlreadyExistsError,
    NoProductionItemsError,
    SlabNotReservedError,
    InvalidWorkOrderTransitionError,
)


@router.get("", response_model=WorkOrderListOut)
def list_work_orders(
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:read")),
) -> WorkOrderListOut:
    repo = WorkOrderRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        status=status,
        search=search,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return WorkOrderListOut(items=[WorkOrderOut.model_validate(o) for o in page], next_cursor=next_cursor)


@router.post("", response_model=WorkOrderOut)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> WorkOrderOut:
    uc = CreateWorkOrderUseCase(db)
    try:
        work_order = uc.execute(
            CreateWorkOrderInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                order_id=payload.order_id,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(work_order)
    return WorkOrderOut.model_validate(work_order)


@router.get("/{work_order_id}", response_model=WorkOrderOut)
def get_work_order(
    work_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:read")),
) -> WorkOrderOut:
    work_order = WorkOrderRepository(db).get(
        company_id=current_user.active_company_id, work_order_id=work_order_id
    )
    if work_order is None:
        raise NotFoundError("Work order not found")
    return WorkOrderOut.model_validate(work_order)


@router.get("/by-order/{order_id}", response_model=WorkOrderOut)
def get_work_order_for_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:read")),
) -> WorkOrderOut:
    work_order = WorkOrderRepository(db).get_for_order(
        company_id=current_user.active_company_id, order_id=order_id
    )
    if work_order is None:
        raise NotFoundError("This order has no work order yet")
    return WorkOrderOut.model_validate(work_order)


@router.post("/{work_order_id}/status", response_model=WorkOrderOut)
def update_work_order_status(
    work_order_id: uuid.UUID,
    payload: WorkOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:write")),
) -> WorkOrderOut:
    uc = UpdateWorkOrderStatusUseCase(db)
    try:
        work_order = uc.execute(
            UpdateWorkOrderStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                work_order_id=work_order_id,
                status=payload.status,
                cancelled_reason=payload.cancelled_reason,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(work_order)
    return WorkOrderOut.model_validate(work_order)


@router.get("/{work_order_id}/items", response_model=WorkOrderItemListOut)
def list_work_order_items(
    work_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("production:read")),
) -> WorkOrderItemListOut:
    rows = WorkOrderItemRepository(db).list_with_details(
        company_id=current_user.active_company_id, work_order_id=work_order_id
    )
    return WorkOrderItemListOut(
        items=[
            WorkOrderItemOut(
                id=woi.id,
                order_item_id=woi.order_item_id,
                slab_id=woi.slab_id,
                slab_number=slab.slab_number,
                description=order_item.description,
                quantity=order_item.quantity,
                unit=order_item.unit,
                area_m2=slab.area_m2,
            )
            for woi, order_item, slab in rows
        ]
    )
