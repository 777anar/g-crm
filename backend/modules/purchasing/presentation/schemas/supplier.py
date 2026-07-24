import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from modules.purchasing.domain.value_objects import VALID_SUPPLIER_STATUSES


class SupplierCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    default_currency: str = Field(default="AZN", min_length=3, max_length=3)


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(default=None)
    tax_id: Optional[str] = None
    payment_terms_days: Optional[int] = Field(default=None, ge=0, le=365)
    default_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)

    def model_post_init(self, __context) -> None:
        if self.status is not None and self.status not in VALID_SUPPLIER_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_SUPPLIER_STATUSES)}")


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    contact_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    notes: Optional[str]
    status: str
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    tax_id: Optional[str]
    payment_terms_days: int
    default_currency: str
    rating: float


class SupplierListOut(BaseModel):
    items: List[SupplierOut]
    next_cursor: Optional[str] = None
