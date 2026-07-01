import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.sales.domain.value_objects import VALID_ITEM_TYPES, VALID_UNITS


class ItemCreate(BaseModel):
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

    def model_post_init(self, __context):
        if self.item_type not in VALID_ITEM_TYPES:
            raise ValueError(f"Invalid item_type: {self.item_type}")
        if self.unit and self.unit not in VALID_UNITS:
            raise ValueError(f"Invalid unit: {self.unit}")


class ItemUpdate(BaseModel):
    description: Optional[str] = None
    material_id: Optional[uuid.UUID] = None
    slab_id: Optional[uuid.UUID] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_sale_price: Optional[Decimal] = None
    unit_cost_price: Optional[Decimal] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


class ItemOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    section_id: uuid.UUID
    quote_id: uuid.UUID
    item_type: str
    sort_order: int
    description: str
    material_id: Optional[uuid.UUID]
    slab_id: Optional[uuid.UUID]
    quantity: Decimal
    unit: str
    unit_sale_price: Decimal
    unit_cost_price: Decimal
    line_total_sale: Decimal
    line_total_cost: Decimal
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ItemListOut(BaseModel):
    items: List[ItemOut]
