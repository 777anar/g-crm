import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from modules.catalog.domain.value_objects import DEFAULT_SLAB_STATUS, VALID_SLAB_STATUSES


class SlabCreate(BaseModel):
    material_id: uuid.UUID
    warehouse_id: uuid.UUID
    slab_number: str
    lot_number: Optional[str] = None
    barcode: Optional[str] = None
    rack_location: Optional[str] = None
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    status: str = DEFAULT_SLAB_STATUS

    def model_post_init(self, __context) -> None:
        if self.status not in VALID_SLAB_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_SLAB_STATUSES)}")


class SlabStatusUpdate(BaseModel):
    status: str

    def model_post_init(self, __context) -> None:
        if self.status not in VALID_SLAB_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_SLAB_STATUSES)}")


class SlabOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    warehouse_id: uuid.UUID
    slab_number: str
    lot_number: Optional[str]
    barcode: Optional[str]
    rack_location: Optional[str]
    length_mm: Optional[Decimal]
    width_mm: Optional[Decimal]
    area_m2: Optional[Decimal]
    weight_kg: Optional[Decimal]
    status: str
    parent_slab_id: Optional[uuid.UUID] = None
    is_offcut: bool = False
    image_document_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class SlabListOut(BaseModel):
    items: list[SlabOut]
    next_cursor: Optional[str] = None


class OffcutListOut(BaseModel):
    """Offcut Library search results (Phase 2). Unlike the main Slab list,
    this is unbounded per page up to a generous cap rather than cursor-
    paginated -- offcut inventory is naturally small per company (it's a
    subset of an already-small slab table), the same "genuinely small,
    per-tenant" reasoning this codebase already applies to Warehouses/
    Price Lists."""

    items: list[SlabOut]


class SlabReservationCreate(BaseModel):
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    notes: Optional[str] = None


class SlabReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slab_id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    status: str
    notes: Optional[str]
    reserved_by: Optional[uuid.UUID]
    reserved_at: Optional[datetime]
    released_at: Optional[datetime]
    created_at: datetime


class SlabReservationListOut(BaseModel):
    items: list[SlabReservationOut]
    next_cursor: Optional[str] = None


class OffcutCreate(BaseModel):
    warehouse_id: uuid.UUID
    slab_number: str
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    notes: Optional[str] = None
