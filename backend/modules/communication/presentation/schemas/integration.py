import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TestConnectionOut(BaseModel):
    ok: bool
    detail: str
    health_status: str


class MessageQueueEntryOut(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    channel_id: uuid.UUID
    status: str
    attempts: int
    max_attempts: int
    next_attempt_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageQueueListOut(BaseModel):
    items: List[MessageQueueEntryOut]


class ProcessQueueOut(BaseModel):
    processed: int
    sent: int
    failed: int
    still_pending: int


class IntegrationLogEntryOut(BaseModel):
    id: uuid.UUID
    channel_id: Optional[uuid.UUID]
    provider: str
    direction: str
    action: str
    success: bool
    status_code: Optional[int]
    signature_valid: Optional[bool]
    error_message: Optional[str]
    duration_ms: Optional[int]
    payload: Optional[Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class IntegrationLogListOut(BaseModel):
    items: List[IntegrationLogEntryOut]


class ImapSyncOut(BaseModel):
    synced_count: int


class GenericWebhookAck(BaseModel):
    created_messages: int
    updated_statuses: int
