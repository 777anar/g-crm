import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    module: str
    actor_user_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    diff_json: Optional[dict] = None
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: List[AuditLogOut]
    next_cursor: Optional[str] = None


class RetentionPolicyOut(BaseModel):
    retention_days: Optional[int] = None
    updated_at: Optional[datetime] = None


class RetentionPolicyUpdate(BaseModel):
    retention_days: Optional[int] = None


class RetentionPurgeOut(BaseModel):
    deleted_count: int
