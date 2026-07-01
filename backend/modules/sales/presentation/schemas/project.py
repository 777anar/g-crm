import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.sales.domain.value_objects import VALID_PROJECT_STATUSES, VALID_PROJECT_TYPES


class ProjectCreate(BaseModel):
    customer_id: uuid.UUID
    name: str
    project_type: str = "other"
    address: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None

    def model_post_init(self, __context):
        if self.project_type not in VALID_PROJECT_TYPES:
            raise ValueError(f"Invalid project_type: {self.project_type}")


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    project_type: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    status: Optional[str] = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    customer_id: uuid.UUID
    name: str
    project_type: str
    address: Optional[str]
    notes: Optional[str]
    assigned_to: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListOut(BaseModel):
    items: List[ProjectOut]
    next_cursor: Optional[str] = None
