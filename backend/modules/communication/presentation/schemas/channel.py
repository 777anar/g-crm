import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.communication.domain.value_objects import VALID_CHANNEL_TYPES


class ChannelCreate(BaseModel):
    channel_type: str
    display_name: str
    identifier: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.channel_type not in VALID_CHANNEL_TYPES:
            raise ValueError(f"channel_type must be one of {sorted(VALID_CHANNEL_TYPES)}")


class ChannelUpdate(BaseModel):
    display_name: Optional[str] = None
    identifier: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    channel_type: str
    display_name: str
    identifier: Optional[str]
    is_active: bool
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChannelListOut(BaseModel):
    items: List[ChannelOut]
