import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.installation.domain.value_objects import VALID_CREW_STATUSES


class CrewCreate(BaseModel):
    name: str
    notes: Optional[str] = None


class CrewUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    def model_post_init(self, __context):
        if self.status is not None and self.status not in VALID_CREW_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class CrewOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    status: str
    notes: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrewListOut(BaseModel):
    items: List[CrewOut]


class CrewMemberCreate(BaseModel):
    user_id: uuid.UUID
    is_lead: bool = False


class CrewMemberOut(BaseModel):
    id: uuid.UUID
    crew_id: uuid.UUID
    user_id: uuid.UUID
    is_lead: bool
    full_name: str
    email: str


class CrewMemberListOut(BaseModel):
    items: List[CrewMemberOut]
