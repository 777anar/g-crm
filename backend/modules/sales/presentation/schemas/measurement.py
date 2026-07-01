import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class MeasurementCreate(BaseModel):
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


class MeasurementUpdate(BaseModel):
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


class MeasurementOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    section_id: uuid.UUID
    quote_id: uuid.UUID
    sort_order: int
    label: Optional[str]
    length_mm: Optional[Decimal]
    width_mm: Optional[Decimal]
    thickness_mm: Optional[Decimal]
    quantity: int
    area_m2: Optional[Decimal]
    waste_pct: Decimal
    required_area_m2: Optional[Decimal]
    override_required_area: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MeasurementListOut(BaseModel):
    items: List[MeasurementOut]
