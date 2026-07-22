import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.production.domain.value_objects import VALID_PRIORITIES, VALID_WORK_ORDER_STATUSES


class WorkOrderCreate(BaseModel):
    order_id: uuid.UUID
    priority: Optional[str] = None
    due_date: Optional[str] = None


class WorkOrderStatusUpdate(BaseModel):
    status: str
    cancelled_reason: Optional[str] = None

    def model_post_init(self, __context):
        if self.status not in VALID_WORK_ORDER_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class WorkOrderUpdate(BaseModel):
    due_date: Optional[str] = None
    notes: Optional[str] = None


class WorkOrderPriorityUpdate(BaseModel):
    priority: str

    def model_post_init(self, __context):
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_PRIORITIES)}")


class WorkOrderOperatorAssign(BaseModel):
    operator_user_id: Optional[uuid.UUID] = None


class WorkOrderStageAssign(BaseModel):
    stage_id: Optional[uuid.UUID] = None


class WorkOrderOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: uuid.UUID
    work_order_number: str
    status: str
    priority: str
    current_stage_id: Optional[uuid.UUID] = None
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


class ProductionJobItemOut(BaseModel):
    """One reserved slab on a Production Job, enriched with the material
    spec (material name/thickness/finish) so the job page never has to
    make a second round-trip per item."""

    id: uuid.UUID
    order_item_id: uuid.UUID
    slab_id: uuid.UUID
    slab_number: str
    description: str
    quantity: Decimal
    unit: str
    area_m2: Optional[Decimal]
    material_id: uuid.UUID
    material_name: str
    thickness_mm: Optional[str]
    finish: Optional[str]


class EntityRef(BaseModel):
    id: uuid.UUID
    name: str


class StageRef(BaseModel):
    id: uuid.UUID
    name: str


class ProductionJobOut(BaseModel):
    """The enriched "Production Job" view: everything requirement #3 asks
    a production job to display, assembled by joining Order -> Customer /
    Project (names only; ids/relationships stay owned by Orders/CRM/Sales)
    and each Work Order Item -> Slab -> Material."""

    id: uuid.UUID
    work_order_number: str
    status: str
    priority: str
    due_date: Optional[str]
    assigned_operator: Optional[uuid.UUID]
    current_stage: Optional[StageRef]
    order: EntityRef
    customer: EntityRef
    project: EntityRef
    items: List[ProductionJobItemOut]
    notes: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]


class WorkOrderEventOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    event_type: str
    from_value: Optional[str]
    to_value: Optional[str]
    notes: Optional[str]
    changed_by: Optional[uuid.UUID]
    changed_at: Optional[datetime]
    created_at: datetime


class WorkOrderTimelineOut(BaseModel):
    items: List[WorkOrderEventOut]


class ProductionStageCreate(BaseModel):
    name: str
    sort_order: Optional[int] = None


class ProductionStageUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProductionStageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    sort_order: int
    is_active: bool


class ProductionStageListOut(BaseModel):
    items: List[ProductionStageOut]
