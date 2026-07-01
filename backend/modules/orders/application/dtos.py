"""Application-layer input DTOs for the Orders module."""
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateOrderInput(ActorContext):
    quote_id: uuid.UUID


@dataclass
class UpdateOrderInput(ActorContext):
    order_id: uuid.UUID
    notes: Optional[str] = None
    production_notes: Optional[str] = None
    installation_notes: Optional[str] = None
    delivery_address: Optional[str] = None
    scheduled_production_date: Optional[str] = None
    scheduled_installation_date: Optional[str] = None


@dataclass
class UpdateOrderStatusInput(ActorContext):
    order_id: uuid.UUID
    status: str
    cancelled_reason: Optional[str] = None


@dataclass
class UpdateOrderItemInput(ActorContext):
    item_id: uuid.UUID
    production_status: Optional[str] = None
    installation_status: Optional[str] = None
    notes: Optional[str] = None
