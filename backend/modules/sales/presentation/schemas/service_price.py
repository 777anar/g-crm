import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel


class ServicePriceUpsert(BaseModel):
    service_key: str
    sale_price: Decimal = Decimal("0")
    cost_price: Decimal = Decimal("0")


class ServicePriceOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    service_key: str
    sale_price: Decimal
    cost_price: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServicePriceListOut(BaseModel):
    items: List[ServicePriceOut]
