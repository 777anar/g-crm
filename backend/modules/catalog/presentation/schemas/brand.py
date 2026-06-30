import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS, VALID_ENTITY_STATUSES


class BrandCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo_document_id: Optional[uuid.UUID] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_document_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(default=None)

    def model_post_init(self, __context) -> None:
        if self.status is not None and self.status not in VALID_ENTITY_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_ENTITY_STATUSES)}")


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    logo_document_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime


class BrandListOut(BaseModel):
    items: list[BrandOut]
