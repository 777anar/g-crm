import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.purchasing.domain.value_objects import MANUALLY_SETTABLE_PURCHASE_ORDER_STATUSES


class PurchaseOrderLineCreate(BaseModel):
    description: str
    quantity: Decimal
    material_id: Optional[uuid.UUID] = None
    unit: str = "unit"
    unit_cost: Decimal = Decimal("0")

    def model_post_init(self, __context) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        if self.unit_cost < 0:
            raise ValueError("unit_cost cannot be negative")


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    lines: List[PurchaseOrderLineCreate]
    currency: str = "AZN"
    notes: Optional[str] = None
    expected_delivery_date: Optional[str] = None


class PurchaseOrderUpdate(BaseModel):
    notes: Optional[str] = None
    expected_delivery_date: Optional[str] = None


class PurchaseOrderStatusUpdate(BaseModel):
    status: str
    cancelled_reason: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.status not in MANUALLY_SETTABLE_PURCHASE_ORDER_STATUSES:
            raise ValueError(f"status must be one of {sorted(MANUALLY_SETTABLE_PURCHASE_ORDER_STATUSES)}")


class PurchaseOrderOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    supplier_id: uuid.UUID
    po_number: str
    status: str
    currency: str
    notes: Optional[str]
    expected_delivery_date: Optional[str]
    subtotal_amount: Decimal
    total_amount: Decimal
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PurchaseOrderListOut(BaseModel):
    items: List[PurchaseOrderOut]
    next_cursor: Optional[str] = None


class PurchaseOrderLineOut(BaseModel):
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    material_id: Optional[uuid.UUID]
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    line_total: Decimal
    quantity_received: Decimal
    sort_order: int

    model_config = {"from_attributes": True}


class PurchaseOrderLineListOut(BaseModel):
    items: List[PurchaseOrderLineOut]


class ReceiveLineRequest(BaseModel):
    quantity_received: Decimal
    notes: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    slab_number: Optional[str] = None
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None

    def model_post_init(self, __context) -> None:
        if self.quantity_received <= 0:
            raise ValueError("quantity_received must be greater than 0")


class GoodsReceiptOut(BaseModel):
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    purchase_order_line_id: uuid.UUID
    slab_id: Optional[uuid.UUID]
    quantity_received: Decimal
    notes: Optional[str]
    received_by: Optional[uuid.UUID]
    received_at: datetime

    model_config = {"from_attributes": True}


class GoodsReceiptListOut(BaseModel):
    items: List[GoodsReceiptOut]
