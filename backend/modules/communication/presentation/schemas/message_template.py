import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.communication.domain.value_objects import VALID_CHANNEL_TYPES


class MessageTemplateCreate(BaseModel):
    name: str
    body: str
    channel_type: Optional[str] = None
    shortcut: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.channel_type is not None and self.channel_type not in VALID_CHANNEL_TYPES:
            raise ValueError(f"channel_type must be one of {sorted(VALID_CHANNEL_TYPES)}")


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = None
    body: Optional[str] = None
    channel_type: Optional[str] = None
    shortcut: Optional[str] = None
    is_active: Optional[bool] = None

    def model_post_init(self, __context) -> None:
        if self.channel_type is not None and self.channel_type not in VALID_CHANNEL_TYPES:
            raise ValueError(f"channel_type must be one of {sorted(VALID_CHANNEL_TYPES)}")


class MessageTemplateOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    channel_type: Optional[str]
    shortcut: Optional[str]
    body: str
    is_active: bool
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageTemplateListOut(BaseModel):
    items: List[MessageTemplateOut]
