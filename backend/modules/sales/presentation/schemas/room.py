import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.sales.domain.value_objects import VALID_ROOM_TYPES


class RoomCreate(BaseModel):
    room_type: str = "custom"
    name: Optional[str] = None
    notes: Optional[str] = None
    sort_order: int = 0

    def model_post_init(self, __context):
        if self.room_type not in VALID_ROOM_TYPES:
            raise ValueError(f"Invalid room_type: {self.room_type}")


class RoomUpdate(BaseModel):
    room_type: Optional[str] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


class RoomOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_id: uuid.UUID
    room_type: str
    name: Optional[str]
    notes: Optional[str]
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoomListOut(BaseModel):
    items: List[RoomOut]
