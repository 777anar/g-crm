import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.sales.domain.value_objects import VALID_QUOTE_STATUSES


class QuoteCreate(BaseModel):
    currency: str = "AZN"
    price_list_id: Optional[uuid.UUID] = None
    valid_until: Optional[str] = None
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    vat_rate: Decimal = Decimal("18")
    discount_type: str = "none"
    discount_value: Decimal = Decimal("0")


class QuoteUpdate(BaseModel):
    currency: Optional[str] = None
    price_list_id: Optional[uuid.UUID] = None
    valid_until: Optional[str] = None
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None


class QuoteStatusUpdate(BaseModel):
    status: str

    def model_post_init(self, __context):
        if self.status not in VALID_QUOTE_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class QuoteOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    customer_id: uuid.UUID
    version: int
    quote_number: str
    status: str
    currency: str
    price_list_id: Optional[uuid.UUID]
    valid_until: Optional[str]
    internal_notes: Optional[str]
    customer_notes: Optional[str]
    prepared_by: Optional[uuid.UUID]
    sent_at: Optional[datetime]
    accepted_at: Optional[datetime]
    rejected_at: Optional[datetime]
    subtotal_gross: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    subtotal_after_discount: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_final: Decimal
    total_internal_cost: Decimal
    total_profit: Decimal
    profit_margin_pct: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuoteListOut(BaseModel):
    items: List[QuoteOut]
    next_cursor: Optional[str] = None
