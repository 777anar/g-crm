import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from modules.catalog.domain.value_objects import DEFAULT_MATERIAL_STATUS, VALID_MATERIAL_STATUSES


class MaterialCreate(BaseModel):
    brand_id: uuid.UUID
    collection_id: Optional[uuid.UUID] = None
    name: str
    material_type: Optional[str] = None
    color: Optional[str] = None
    finish: Optional[str] = None
    thickness_mm: Optional[str] = None
    dimensions: Optional[str] = None
    country_of_origin: Optional[str] = None
    description: Optional[str] = None
    status: str = DEFAULT_MATERIAL_STATUS

    def model_post_init(self, __context) -> None:
        if self.status not in VALID_MATERIAL_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_MATERIAL_STATUSES)}")


class MaterialUpdate(BaseModel):
    brand_id: Optional[uuid.UUID] = None
    collection_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    material_type: Optional[str] = None
    color: Optional[str] = None
    finish: Optional[str] = None
    thickness_mm: Optional[str] = None
    dimensions: Optional[str] = None
    country_of_origin: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.status is not None and self.status not in VALID_MATERIAL_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_MATERIAL_STATUSES)}")


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_id: uuid.UUID
    collection_id: Optional[uuid.UUID]
    name: str
    material_type: Optional[str]
    color: Optional[str]
    finish: Optional[str]
    thickness_mm: Optional[str]
    dimensions: Optional[str]
    country_of_origin: Optional[str]
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class MaterialListOut(BaseModel):
    items: list[MaterialOut]
    next_cursor: Optional[str] = None
