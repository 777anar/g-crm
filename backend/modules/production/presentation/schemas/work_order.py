import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.production.domain.value_objects import VALID_WORK_ORDER_STATUSES


class WorkOrderCreate(BaseModel):
    order_id: uuid.UUID


class WorkOrderStatusUpdate(BaseModel):
    status: str
    cancelled_reason: Optional[str] = None

    def model_post_init(self, __context):
        if self.status not in VALID_WORK_ORDER_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class WorkOrderOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: uuid.UUID
    work_order_number: str
    status: str
    assigned_to: Optional[uuid.UUID]
    scheduled_start_date: Optional[str]
    scheduled_completion_date: Optional[str]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    notes: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderListOut(BaseModel):
    items: List[WorkOrderOut]
    next_cursor: Optional[str] = None


class WorkOrderItemOut(BaseModel):
    id: uuid.UUID
    order_item_id: uuid.UUID
    slab_id: uuid.UUID
    slab_number: str
    description: str
    quantity: Decimal
    unit: str
    area_m2: Optional[Decimal]


class WorkOrderItemListOut(BaseModel):
    items: List[WorkOrderItemOut]
