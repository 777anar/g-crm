import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.sales.domain.value_objects import VALID_ITEM_TYPES, VALID_UNITS


class ProjectItemCreate(BaseModel):
    item_type: str
    name: Optional[str] = None
    material_id: Optional[uuid.UUID] = None
    material_thickness_id: Optional[uuid.UUID] = None
    material_size_id: Optional[uuid.UUID] = None
    quantity: Decimal = Decimal("1")
    unit: Optional[str] = None
    notes: Optional[str] = None
    sort_order: int = 0

    def model_post_init(self, __context):
        if self.item_type not in VALID_ITEM_TYPES:
            raise ValueError(f"Invalid item_type: {self.item_type}")
        if self.unit and self.unit not in VALID_UNITS:
            raise ValueError(f"Invalid unit: {self.unit}")


class ProjectItemUpdate(BaseModel):
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


class ProjectItemOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    room_id: uuid.UUID
    item_type: str
    name: Optional[str]
    material_id: Optional[uuid.UUID]
    material_thickness_id: Optional[uuid.UUID]
    material_size_id: Optional[uuid.UUID]
    quantity: Decimal
    unit: str
    notes: Optional[str]
    production_status: Optional[str]
    installation_status: Optional[str]
    completion_status: Optional[str]
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectItemListOut(BaseModel):
    items: List[ProjectItemOut]
