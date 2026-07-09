import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.sales.domain.value_objects import VALID_MEASUREMENT_STATUSES


class ProjectItemMeasurementCreate(BaseModel):
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    quantity: int = 1
    measurer_name: str = ""
    measured_at: Optional[date] = None
    notes: Optional[str] = None
    status: str = "draft"

    def model_post_init(self, __context):
        if self.status not in VALID_MEASUREMENT_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class ProjectItemMeasurementUpdate(BaseModel):
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    quantity: Optional[int] = None
    measurer_name: Optional[str] = None
    measured_at: Optional[date] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    customer_signature_document_id: Optional[uuid.UUID] = None


class ProjectItemMeasurementOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_item_id: uuid.UUID
    revision_number: int
    status: str
    length_mm: Optional[Decimal]
    width_mm: Optional[Decimal]
    thickness_mm: Optional[Decimal]
    quantity: int
    area_m2: Optional[Decimal]
    measurer_name: str
    measured_at: Optional[date]
    notes: Optional[str]
    customer_signature_document_id: Optional[uuid.UUID]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectItemMeasurementListOut(BaseModel):
    items: List[ProjectItemMeasurementOut]
