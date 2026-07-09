import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialThicknessCreate(BaseModel):
    thickness_mm: str
    sort_order: int = 0


class MaterialThicknessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    thickness_mm: str
    sort_order: int
    created_at: datetime


class MaterialThicknessListOut(BaseModel):
    items: list[MaterialThicknessOut]


class MaterialSizeCreate(BaseModel):
    dimensions: str
    sort_order: int = 0


class MaterialSizeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    dimensions: str
    sort_order: int
    created_at: datetime


class MaterialSizeListOut(BaseModel):
    items: list[MaterialSizeOut]
