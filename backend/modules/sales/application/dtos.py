"""Application-layer input DTOs — framework-free dataclasses."""
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


# ── Project ───────────────────────────────────────────────────────────────────

@dataclass
class CreateProjectInput(ActorContext):
    customer_id: uuid.UUID
    name: str
    project_type: str = "other"
    address: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None


@dataclass
class UpdateProjectInput(ActorContext):
    project_id: uuid.UUID
    name: Optional[str] = None
    project_type: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    status: Optional[str] = None


# ── Quote ─────────────────────────────────────────────────────────────────────

@dataclass
class CreateQuoteInput(ActorContext):
    project_id: uuid.UUID
    currency: str = "AZN"
    price_list_id: Optional[uuid.UUID] = None
    valid_until: Optional[str] = None
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    vat_rate: Decimal = Decimal("18")
    discount_type: str = "none"
    discount_value: Decimal = Decimal("0")


@dataclass
class UpdateQuoteInput(ActorContext):
    quote_id: uuid.UUID
    currency: Optional[str] = None
    price_list_id: Optional[uuid.UUID] = None
    valid_until: Optional[str] = None
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None


@dataclass
class UpdateQuoteStatusInput(ActorContext):
    quote_id: uuid.UUID
    status: str


# ── Section ───────────────────────────────────────────────────────────────────

@dataclass
class CreateSectionInput(ActorContext):
    quote_id: uuid.UUID
    name: str
    sort_order: int = 0
    notes: Optional[str] = None


@dataclass
class UpdateSectionInput(ActorContext):
    section_id: uuid.UUID
    name: Optional[str] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


# ── Measurement ───────────────────────────────────────────────────────────────

@dataclass
class CreateMeasurementInput(ActorContext):
    section_id: uuid.UUID
    label: Optional[str] = None
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    quantity: int = 1
    waste_pct: Decimal = Decimal("10")
    override_required_area: bool = False
    required_area_m2: Optional[Decimal] = None
    notes: Optional[str] = None
    sort_order: int = 0


@dataclass
class UpdateMeasurementInput(ActorContext):
    measurement_id: uuid.UUID
    label: Optional[str] = None
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    quantity: Optional[int] = None
    waste_pct: Optional[Decimal] = None
    override_required_area: Optional[bool] = None
    required_area_m2: Optional[Decimal] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


# ── Section Item ──────────────────────────────────────────────────────────────

@dataclass
class CreateItemInput(ActorContext):
    section_id: uuid.UUID
    item_type: str
    description: str = ""
    material_id: Optional[uuid.UUID] = None
    slab_id: Optional[uuid.UUID] = None
    quantity: Decimal = Decimal("1")
    unit: Optional[str] = None
    unit_sale_price: Decimal = Decimal("0")
    unit_cost_price: Decimal = Decimal("0")
    notes: Optional[str] = None
    sort_order: int = 0


@dataclass
class UpdateItemInput(ActorContext):
    item_id: uuid.UUID
    description: Optional[str] = None
    material_id: Optional[uuid.UUID] = None
    slab_id: Optional[uuid.UUID] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_sale_price: Optional[Decimal] = None
    unit_cost_price: Optional[Decimal] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


# ── Service Price ─────────────────────────────────────────────────────────────

@dataclass
class UpsertServicePriceInput(ActorContext):
    service_key: str
    sale_price: Decimal = Decimal("0")
    cost_price: Decimal = Decimal("0")


# ── Room (Sprint 3: Project workspace) ────────────────────────────────────────

@dataclass
class CreateRoomInput(ActorContext):
    project_id: uuid.UUID
    room_type: str = "custom"
    name: Optional[str] = None
    notes: Optional[str] = None
    sort_order: int = 0


@dataclass
class UpdateRoomInput(ActorContext):
    room_id: uuid.UUID
    room_type: Optional[str] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


# ── Project Item ───────────────────────────────────────────────────────────────

@dataclass
class CreateProjectItemInput(ActorContext):
    room_id: uuid.UUID
    item_type: str
    name: Optional[str] = None
    material_id: Optional[uuid.UUID] = None
    material_thickness_id: Optional[uuid.UUID] = None
    material_size_id: Optional[uuid.UUID] = None
    quantity: Decimal = Decimal("1")
    unit: Optional[str] = None
    notes: Optional[str] = None
    sort_order: int = 0


@dataclass
class UpdateProjectItemInput(ActorContext):
    project_item_id: uuid.UUID
    item_type: Optional[str] = None
    name: Optional[str] = None
    material_id: Optional[uuid.UUID] = None
    material_thickness_id: Optional[uuid.UUID] = None
    material_size_id: Optional[uuid.UUID] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None
    production_status: Optional[str] = None
    installation_status: Optional[str] = None
    completion_status: Optional[str] = None


# ── Project Item Measurement ───────────────────────────────────────────────────

@dataclass
class CreateProjectItemMeasurementInput(ActorContext):
    project_item_id: uuid.UUID
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    quantity: int = 1
    measurer_name: str = ""
    measured_at: Optional[date] = None
    notes: Optional[str] = None
    status: str = "draft"


@dataclass
class UpdateProjectItemMeasurementInput(ActorContext):
    measurement_id: uuid.UUID
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    quantity: Optional[int] = None
    measurer_name: Optional[str] = None
    measured_at: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    customer_signature_document_id: Optional[uuid.UUID] = None


# ── Project Item Drawing / Photo ───────────────────────────────────────────────

@dataclass
class AddProjectItemDrawingInput(ActorContext):
    project_item_id: uuid.UUID
    document_id: uuid.UUID
    drawing_type: str = "sketch"
    label: Optional[str] = None
    sort_order: int = 0


@dataclass
class AddProjectItemPhotoInput(ActorContext):
    project_item_id: uuid.UUID
    document_id: uuid.UUID
    caption: Optional[str] = None
    sort_order: int = 0
