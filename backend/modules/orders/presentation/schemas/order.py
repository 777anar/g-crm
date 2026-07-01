import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.orders.domain.value_objects import VALID_ORDER_STATUSES


class OrderCreate(BaseModel):
    quote_id: uuid.UUID


class OrderUpdate(BaseModel):
    notes: Optional[str] = None
    production_notes: Optional[str] = None
    installation_notes: Optional[str] = None
    delivery_address: Optional[str] = None
    scheduled_production_date: Optional[str] = None
    scheduled_installation_date: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: str
    cancelled_reason: Optional[str] = None

    def model_post_init(self, __context):
        if self.status not in VALID_ORDER_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class OrderOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    customer_id: uuid.UUID
    quote_id: uuid.UUID
    order_number: str
    status: str
    currency: str
    notes: Optional[str]
    production_notes: Optional[str]
    installation_notes: Optional[str]
    delivery_address: Optional[str]
    scheduled_production_date: Optional[str]
    scheduled_installation_date: Optional[str]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    created_by: Optional[uuid.UUID]
    subtotal_gross: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    subtotal_after_discount: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_final: Decimal
    total_internal_cost: Decimal
    total_profit: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListOut(BaseModel):
    items: List[OrderOut]
    next_cursor: Optional[str] = None


class OrderSectionOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: uuid.UUID
    name: str
    sort_order: int
    notes: Optional[str]
    total_measured_area: Optional[Decimal]
    subtotal_sale: Decimal
    subtotal_cost: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderSectionListOut(BaseModel):
    items: List[OrderSectionOut]


class OrderItemOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: uuid.UUID
    section_id: uuid.UUID
    item_type: str
    sort_order: int
    description: str
    material_id: Optional[uuid.UUID]
    slab_id: Optional[uuid.UUID]
    quantity: Decimal
    unit: str
    unit_sale_price: Decimal
    unit_cost_price: Decimal
    line_total_sale: Decimal
    line_total_cost: Decimal
    notes: Optional[str]
    production_status: Optional[str]
    installation_status: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderItemListOut(BaseModel):
    items: List[OrderItemOut]


class OrderItemUpdate(BaseModel):
    production_status: Optional[str] = None
    installation_status: Optional[str] = None
    notes: Optional[str] = None


class OrderMeasurementOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: uuid.UUID
    section_id: uuid.UUID
    sort_order: int
    label: Optional[str]
    length_mm: Optional[Decimal]
    width_mm: Optional[Decimal]
    thickness_mm: Optional[Decimal]
    quantity: int
    area_m2: Optional[Decimal]
    required_area_m2: Optional[Decimal]
    waste_pct: Decimal
    override_required_area: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderMeasurementListOut(BaseModel):
    items: List[OrderMeasurementOut]
