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


@dataclass
class UpdateWorkOrderStatusInput(ActorContext):
    work_order_id: uuid.UUID
    status: str
    cancelled_reason: Optional[str] = None
