"""Application-layer input DTOs for the Production module."""
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateWorkOrderInput(ActorContext):
    order_id: uuid.UUID
    priority: Optional[str] = None
    due_date: Optional[str] = None


@dataclass
class UpdateWorkOrderStatusInput(ActorContext):
    work_order_id: uuid.UUID
    status: str
    cancelled_reason: Optional[str] = None


@dataclass
class UpdateWorkOrderInput(ActorContext):
    work_order_id: uuid.UUID
    due_date: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class UpdateWorkOrderPriorityInput(ActorContext):
    work_order_id: uuid.UUID
    priority: str


@dataclass
class AssignWorkOrderOperatorInput(ActorContext):
    work_order_id: uuid.UUID
    operator_user_id: Optional[uuid.UUID]


@dataclass
class UpdateWorkOrderStageInput(ActorContext):
    work_order_id: uuid.UUID
    stage_id: Optional[uuid.UUID]


@dataclass
class CreateProductionStageInput(ActorContext):
    name: str
    sort_order: Optional[int] = None


@dataclass
class UpdateProductionStageInput(ActorContext):
    stage_id: uuid.UUID
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


@dataclass
class MarkNotificationReadInput(ActorContext):
    notification_id: uuid.UUID
