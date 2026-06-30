import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PriceListCreate(BaseModel):
    name: str
    currency: str = "AZN"
    is_default: bool = False


class PriceListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    currency: str
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime


class PriceListListOut(BaseModel):
    items: list[PriceListOut]


class PriceListEntryUpsert(BaseModel):
    material_id: uuid.UUID
    cost_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")


class PriceListEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    price_list_id: uuid.UUID
    material_id: uuid.UUID
    cost_price: Decimal
    sale_price: Decimal


class PriceListEntryListOut(BaseModel):
    items: list[PriceListEntryOut]
