import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class SectionCreate(BaseModel):
    name: str
    sort_order: int = 0
    notes: Optional[str] = None


class SectionUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class SectionOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    quote_id: uuid.UUID
    name: str
    sort_order: int
    notes: Optional[str]
    total_measured_area: Optional[Decimal]
    subtotal_sale: Decimal
    subtotal_cost: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionListOut(BaseModel):
    items: List[SectionOut]
