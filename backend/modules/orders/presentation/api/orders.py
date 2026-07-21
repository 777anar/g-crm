import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, NotFoundError
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.orders.application.dtos import (
    CreateOrderInput,
    UpdateOrderInput,
    UpdateOrderItemInput,
    UpdateOrderStatusInput,
)
from modules.orders.application.use_cases import (
    CreateOrderUseCase,
    UpdateOrderItemUseCase,
    UpdateOrderStatusUseCase,
    UpdateOrderUseCase,
)
from modules.orders.domain.exceptions import (
    InvalidOrderTransitionError,
    OrderImmutableError,
    QuoteNotAcceptedError,
)
from modules.orders.infrastructure.repositories.order_item_repository import OrderItemRepository
from modules.orders.infrastructure.repositories.order_measurement_repository import OrderMeasurementRepository
from modules.orders.infrastructure.repositories.order_repository import OrderRepository
from modules.orders.infrastructure.repositories.order_section_repository import OrderSectionRepository
from modules.orders.presentation.schemas.order import (
    OrderCreate,
    OrderItemListOut,
    OrderItemOut,
    OrderItemUpdate,
    OrderListOut,
    OrderMeasurementListOut,
    OrderOut,
    OrderSectionListOut,
    OrderStatusUpdate,
    OrderUpdate,
)

router = APIRouter()


@router.get("", response_model=OrderListOut)
def list_orders(
    project_id: Optional[uuid.UUID] = Query(default=None),
    customer_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:read")),
) -> OrderListOut:
    repo = OrderRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        project_id=project_id,
        customer_id=customer_id,
        status=status,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return OrderListOut(
        items=[OrderOut.model_validate(o) for o in page],
        next_cursor=next_cursor,
    )


@router.post("", response_model=OrderOut)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:write")),
) -> OrderOut:
    uc = CreateOrderUseCase(db)
    try:
        order = uc.execute(
            CreateOrderInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                quote_id=payload.quote_id,
            )
        )
    except QuoteNotAcceptedError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:read")),
) -> OrderOut:
    order = OrderRepository(db).get(
        company_id=current_user.active_company_id, order_id=order_id
    )
    if order is None:
        raise NotFoundError("Order not found")
    return OrderOut.model_validate(order)


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: uuid.UUID,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:write")),
) -> OrderOut:
    uc = UpdateOrderUseCase(db)
    try:
        order = uc.execute(
            UpdateOrderInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                order_id=order_id,
                notes=payload.notes,
                production_notes=payload.production_notes,
                installation_notes=payload.installation_notes,
                delivery_address=payload.delivery_address,
                scheduled_production_date=payload.scheduled_production_date,
                scheduled_installation_date=payload.scheduled_installation_date,
            )
        )
    except OrderImmutableError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


@router.post("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:write")),
) -> OrderOut:
    uc = UpdateOrderStatusUseCase(db)
    try:
        order = uc.execute(
            UpdateOrderStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                order_id=order_id,
                status=payload.status,
                cancelled_reason=payload.cancelled_reason,
            )
        )
    except InvalidOrderTransitionError as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


@router.get("/{order_id}/sections", response_model=OrderSectionListOut)
def list_order_sections(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:read")),
) -> OrderSectionListOut:
    sections = OrderSectionRepository(db).list_for_order(
        company_id=current_user.active_company_id, order_id=order_id
    )
    return OrderSectionListOut(items=sections)


@router.get("/{order_id}/sections/{section_id}/items", response_model=OrderItemListOut)
def list_section_items(
    order_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:read")),
) -> OrderItemListOut:
    items = OrderItemRepository(db).list_for_section(
        company_id=current_user.active_company_id, section_id=section_id
    )
    return OrderItemListOut(items=items)


@router.get("/{order_id}/sections/{section_id}/measurements", response_model=OrderMeasurementListOut)
def list_section_measurements(
    order_id: uuid.UUID,
    section_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:read")),
) -> OrderMeasurementListOut:
    measurements = OrderMeasurementRepository(db).list_for_section(
        company_id=current_user.active_company_id, section_id=section_id
    )
    return OrderMeasurementListOut(items=measurements)


@router.patch("/{order_id}/items/{item_id}", response_model=OrderItemOut)
def update_order_item(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: OrderItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("orders:write")),
) -> OrderItemOut:
    uc = UpdateOrderItemUseCase(db)
    item = uc.execute(
        UpdateOrderItemInput(
            company_id=current_user.active_company_id,
            actor_user_id=current_user.user_id,
            item_id=item_id,
            production_status=payload.production_status,
            installation_status=payload.installation_status,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(item)
    return OrderItemOut.model_validate(item)
