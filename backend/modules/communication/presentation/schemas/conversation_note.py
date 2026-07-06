import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ConversationNoteCreate(BaseModel):
    body: str


class ConversationNoteOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    body: str
    created_by: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationNoteListOut(BaseModel):
    items: List[ConversationNoteOut]
