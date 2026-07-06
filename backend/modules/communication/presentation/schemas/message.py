import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.communication.domain.value_objects import VALID_MESSAGE_TYPES


class MessageCreate(BaseModel):
    body: str
    message_type: Optional[str] = None
    template_id: Optional[uuid.UUID] = None

    def model_post_init(self, __context) -> None:
        if self.message_type is not None and self.message_type not in VALID_MESSAGE_TYPES:
            raise ValueError(f"message_type must be one of {sorted(VALID_MESSAGE_TYPES)}")


class InboundMessageCreate(BaseModel):
    channel_id: uuid.UUID
    external_contact_id: str
    body: str
    external_contact_name: Optional[str] = None
    message_type: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.message_type is not None and self.message_type not in VALID_MESSAGE_TYPES:
            raise ValueError(f"message_type must be one of {sorted(VALID_MESSAGE_TYPES)}")


class MessageOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    conversation_id: uuid.UUID
    direction: str
    sender_type: str
    sender_user_id: Optional[uuid.UUID]
    message_type: str
    body: Optional[str]
    template_id: Optional[uuid.UUID]
    external_message_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageListOut(BaseModel):
    items: List[MessageOut]


class MessageAttachmentCreate(BaseModel):
    document_id: uuid.UUID
    file_name: Optional[str] = None


class MessageAttachmentOut(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    document_id: uuid.UUID
    file_name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageAttachmentListOut(BaseModel):
    items: List[MessageAttachmentOut]
