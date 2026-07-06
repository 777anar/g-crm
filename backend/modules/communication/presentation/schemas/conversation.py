import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.communication.domain.value_objects import VALID_CONVERSATION_STATUSES


class ConversationCreate(BaseModel):
    channel_id: uuid.UUID
    external_contact_id: str
    external_contact_name: Optional[str] = None


class ConversationUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    tags: Optional[List[str]] = None
    customer_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    quote_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None

    def model_post_init(self, __context) -> None:
        if self.status is not None and self.status not in VALID_CONVERSATION_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_CONVERSATION_STATUSES)}")


class ConversationOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    channel_id: uuid.UUID
    customer_id: Optional[uuid.UUID]
    lead_id: Optional[uuid.UUID]
    project_id: Optional[uuid.UUID]
    quote_id: Optional[uuid.UUID]
    order_id: Optional[uuid.UUID]
    external_contact_id: str
    external_contact_name: Optional[str]
    status: str
    assigned_to: Optional[uuid.UUID]
    tags: List[str]
    unread_count: int
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListOut(BaseModel):
    items: List[ConversationOut]
    next_cursor: Optional[str] = None
