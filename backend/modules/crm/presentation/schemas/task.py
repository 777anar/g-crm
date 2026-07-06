import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.crm.domain.value_objects import (
    VALID_TASK_PRIORITIES,
    VALID_TASK_RECURRENCE_RULES,
    VALID_TASK_STATUSES,
)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    remind_at: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None
    tags: List[str] = []
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[uuid.UUID] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    recurrence_interval: int = 1
    recurrence_end_date: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.priority is not None and self.priority not in VALID_TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_TASK_PRIORITIES)}")
        if self.recurrence_rule is not None and self.recurrence_rule not in VALID_TASK_RECURRENCE_RULES:
            raise ValueError(f"recurrence_rule must be one of {sorted(VALID_TASK_RECURRENCE_RULES)}")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    remind_at: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None
    tags: Optional[List[str]] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[uuid.UUID] = None
    is_recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = None
    recurrence_interval: Optional[int] = None
    recurrence_end_date: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.priority is not None and self.priority not in VALID_TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_TASK_PRIORITIES)}")
        if self.recurrence_rule is not None and self.recurrence_rule not in VALID_TASK_RECURRENCE_RULES:
            raise ValueError(f"recurrence_rule must be one of {sorted(VALID_TASK_RECURRENCE_RULES)}")


class TaskStatusUpdate(BaseModel):
    status: str
    cancelled_reason: Optional[str] = None

    def model_post_init(self, __context):
        if self.status not in VALID_TASK_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class TaskOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    tags: List[str]
    due_date: Optional[datetime]
    remind_at: Optional[datetime]
    assigned_to: Optional[uuid.UUID]
    related_entity_type: Optional[str]
    related_entity_id: Optional[uuid.UUID]
    is_recurring: bool
    recurrence_rule: Optional[str]
    recurrence_interval: int
    recurrence_end_date: Optional[str]
    series_id: Optional[uuid.UUID]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    items: List[TaskOut]
    next_cursor: Optional[str] = None


class TaskNotificationOut(BaseModel):
    id: uuid.UUID
    notification_type: str
    title: str
    message: str
    task_id: uuid.UUID
    read_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskNotificationListOut(BaseModel):
    items: List[TaskNotificationOut]
