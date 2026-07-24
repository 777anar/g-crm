import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.api.errors import BusinessRuleViolationError, ForbiddenError, NotFoundError
from core.rbac.permissions import role_has_permission
from core.api.pagination import decode_cursor, encode_cursor
from core.db.session import get_db
from core.rbac.dependencies import CurrentUser, require_permission
from modules.purchasing.application.dtos import (
    CreatePurchaseOrderInput,
    PurchaseOrderLineInput,
    ReceivePurchaseOrderLineInput,
    UpdatePurchaseOrderInput,
    UpdatePurchaseOrderStatusInput,
)
from modules.purchasing.application.use_cases import (
    CreatePurchaseOrderUseCase,
    ReceivePurchaseOrderLineUseCase,
    UpdatePurchaseOrderStatusUseCase,
    UpdatePurchaseOrderUseCase,
)
from modules.purchasing.domain.exceptions import (
    EmptyPurchaseOrderError,
    InvalidPurchaseOrderTransitionError,
    InvalidReceiptQuantityError,
    PurchaseOrderImmutableError,
    PurchaseOrderNotReceivableError,
    ReceivedLineHasNoMaterialError,
    SupplierInactiveError,
)
from modules.purchasing.infrastructure.repositories.goods_receipt_repository import GoodsReceiptRepository
from modules.purchasing.infrastructure.repositories.purchase_order_line_repository import (
    PurchaseOrderLineRepository,
)
from modules.purchasing.infrastructure.repositories.purchase_order_repository import PurchaseOrderRepository
from modules.purchasing.presentation.schemas.purchase_order import (
    GoodsReceiptListOut,
    GoodsReceiptOut,
    PurchaseOrderCreate,
    PurchaseOrderLineListOut,
    PurchaseOrderLineOut,
    PurchaseOrderListOut,
    PurchaseOrderOut,
    PurchaseOrderStatusUpdate,
    PurchaseOrderUpdate,
    ReceiveLineRequest,
)

router = APIRouter()

_BUSINESS_RULE_ERRORS = (
    SupplierInactiveError,
    EmptyPurchaseOrderError,
    PurchaseOrderImmutableError,
    InvalidPurchaseOrderTransitionError,
    PurchaseOrderNotReceivableError,
    InvalidReceiptQuantityError,
    ReceivedLineHasNoMaterialError,
)


@router.get("/purchase-orders", response_model=PurchaseOrderListOut)
def list_purchase_orders(
    supplier_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:read")),
) -> PurchaseOrderListOut:
    repo = PurchaseOrderRepository(db)
    offset = decode_cursor(cursor)
    items = repo.list(
        company_id=current_user.active_company_id,
        supplier_id=supplier_id,
        status=status,
        search=search,
        sort=sort,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(items) > limit
    page = items[:limit]
    next_cursor = encode_cursor(offset=offset + limit) if has_more else None
    return PurchaseOrderListOut(items=[PurchaseOrderOut.model_validate(o) for o in page], next_cursor=next_cursor)


@router.post("/purchase-orders", response_model=PurchaseOrderOut)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:write")),
) -> PurchaseOrderOut:
    uc = CreatePurchaseOrderUseCase(db)
    try:
        purchase_order = uc.execute(
            CreatePurchaseOrderInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                supplier_id=payload.supplier_id,
                lines=[
                    PurchaseOrderLineInput(
                        description=line.description,
                        quantity=line.quantity,
                        material_id=line.material_id,
                        unit=line.unit,
                        unit_cost=line.unit_cost,
                    )
                    for line in payload.lines
                ],
                currency=payload.currency,
                notes=payload.notes,
                expected_delivery_date=payload.expected_delivery_date,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(purchase_order)
    return PurchaseOrderOut.model_validate(purchase_order)


@router.get("/purchase-orders/{purchase_order_id}", response_model=PurchaseOrderOut)
def get_purchase_order(
    purchase_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:read")),
) -> PurchaseOrderOut:
    purchase_order = PurchaseOrderRepository(db).get(
        company_id=current_user.active_company_id, purchase_order_id=purchase_order_id
    )
    if purchase_order is None:
        raise NotFoundError("Purchase order not found")
    return PurchaseOrderOut.model_validate(purchase_order)


@router.patch("/purchase-orders/{purchase_order_id}", response_model=PurchaseOrderOut)
def update_purchase_order(
    purchase_order_id: uuid.UUID,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:write")),
) -> PurchaseOrderOut:
    uc = UpdatePurchaseOrderUseCase(db)
    try:
        purchase_order = uc.execute(
            UpdatePurchaseOrderInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                purchase_order_id=purchase_order_id,
                notes=payload.notes,
                expected_delivery_date=payload.expected_delivery_date,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(purchase_order)
    return PurchaseOrderOut.model_validate(purchase_order)


@router.post("/purchase-orders/{purchase_order_id}/status", response_model=PurchaseOrderOut)
def update_purchase_order_status(
    purchase_order_id: uuid.UUID,
    payload: PurchaseOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:write")),
) -> PurchaseOrderOut:
    if payload.status in {"approved", "rejected"} and not role_has_permission(
        role=current_user.role,
        permission="purchasing:purchase_orders:approve",
        module_permission_overrides=current_user.module_permissions,
    ):
        raise ForbiddenError("Purchase order approval requires manager permission")
    uc = UpdatePurchaseOrderStatusUseCase(db)
    try:
        purchase_order = uc.execute(
            UpdatePurchaseOrderStatusInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                purchase_order_id=purchase_order_id,
                status=payload.status,
            cancelled_reason=payload.cancelled_reason,
            approval_notes=payload.approval_notes,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(purchase_order)
    return PurchaseOrderOut.model_validate(purchase_order)


@router.get("/purchase-orders/{purchase_order_id}/lines", response_model=PurchaseOrderLineListOut)
def list_purchase_order_lines(
    purchase_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:read")),
) -> PurchaseOrderLineListOut:
    lines = PurchaseOrderLineRepository(db).list_for_order(
        company_id=current_user.active_company_id, purchase_order_id=purchase_order_id
    )
    return PurchaseOrderLineListOut(items=[PurchaseOrderLineOut.model_validate(line) for line in lines])


@router.post("/purchase-orders/{purchase_order_id}/lines/{line_id}/receive", response_model=GoodsReceiptOut)
def receive_purchase_order_line(
    purchase_order_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: ReceiveLineRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:write")),
) -> GoodsReceiptOut:
    uc = ReceivePurchaseOrderLineUseCase(db)
    try:
        receipt = uc.execute(
            ReceivePurchaseOrderLineInput(
                company_id=current_user.active_company_id,
                actor_user_id=current_user.user_id,
                purchase_order_id=purchase_order_id,
                line_id=line_id,
                quantity_received=payload.quantity_received,
                notes=payload.notes,
                warehouse_id=payload.warehouse_id,
                slab_number=payload.slab_number,
                length_mm=payload.length_mm,
                width_mm=payload.width_mm,
            )
        )
    except _BUSINESS_RULE_ERRORS as exc:
        raise BusinessRuleViolationError(str(exc)) from exc
    db.commit()
    db.refresh(receipt)
    return GoodsReceiptOut.model_validate(receipt)


@router.get("/purchase-orders/{purchase_order_id}/receipts", response_model=GoodsReceiptListOut)
def list_goods_receipts(
    purchase_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("purchasing:purchase_orders:read")),
) -> GoodsReceiptListOut:
    receipts = GoodsReceiptRepository(db).list_for_order(
        company_id=current_user.active_company_id, purchase_order_id=purchase_order_id
    )
    return GoodsReceiptListOut(items=[GoodsReceiptOut.model_validate(r) for r in receipts])
