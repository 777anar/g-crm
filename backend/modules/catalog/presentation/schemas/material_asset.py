import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from modules.catalog.domain.value_objects import IMAGE_TYPE_GALLERY


class MaterialImageCreate(BaseModel):
    document_id: uuid.UUID
    image_type: str = IMAGE_TYPE_GALLERY
    sort_order: int = 0


class MaterialImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    document_id: uuid.UUID
    image_type: str
    sort_order: int
    created_at: datetime


class MaterialImageListOut(BaseModel):
    items: list[MaterialImageOut]


class MaterialDocumentCreate(BaseModel):
    document_id: uuid.UUID
    document_type: str


class MaterialDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    document_id: uuid.UUID
    document_type: str
    created_at: datetime


class MaterialDocumentListOut(BaseModel):
    items: list[MaterialDocumentOut]
