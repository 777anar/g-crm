import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: uuid.UUID
    notification_type: str
    title: str
    message: str
    installation_job_id: Optional[uuid.UUID]
    read_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    items: List[NotificationOut]
