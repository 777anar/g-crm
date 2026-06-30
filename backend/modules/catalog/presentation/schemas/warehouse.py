import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from modules.catalog.domain.value_objects import VALID_ENTITY_STATUSES


class WarehouseCreate(BaseModel):
    name: str
    address: Optional[str] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.status is not None and self.status not in VALID_ENTITY_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_ENTITY_STATUSES)}")


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    address: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class WarehouseListOut(BaseModel):
    items: list[WarehouseOut]
