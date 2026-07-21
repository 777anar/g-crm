"""Application-layer input DTOs. Presentation schemas (Pydantic) map onto
these before calling a use-case, keeping the use-case layer free of any
FastAPI/Pydantic import -- same pattern as every other module."""
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateSupplierInput(ActorContext):
    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class UpdateSupplierInput(ActorContext):
    supplier_id: uuid.UUID
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@dataclass
class PurchaseOrderLineInput:
    description: str
    quantity: Decimal
    material_id: Optional[uuid.UUID] = None
    unit: str = "unit"
    unit_cost: Decimal = Decimal("0")


@dataclass
class CreatePurchaseOrderInput(ActorContext):
    supplier_id: uuid.UUID
    lines: List[PurchaseOrderLineInput] = field(default_factory=list)
    currency: str = "AZN"
    notes: Optional[str] = None
    expected_delivery_date: Optional[str] = None


@dataclass
class UpdatePurchaseOrderInput(ActorContext):
    purchase_order_id: uuid.UUID
    notes: Optional[str] = None
    expected_delivery_date: Optional[str] = None


@dataclass
class UpdatePurchaseOrderStatusInput(ActorContext):
    purchase_order_id: uuid.UUID
    status: str
    cancelled_reason: Optional[str] = None


@dataclass
class ReceivePurchaseOrderLineInput(ActorContext):
    purchase_order_id: uuid.UUID
    line_id: uuid.UUID
    quantity_received: Decimal
    notes: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    slab_number: Optional[str] = None
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
