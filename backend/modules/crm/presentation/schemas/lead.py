import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from modules.crm.domain.value_objects import VALID_LEAD_SOURCES


class LeadCreate(BaseModel):
    full_name: str
    source_channel: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    campaign: Optional[str] = None
    assigned_manager_id: Optional[uuid.UUID] = None

    def model_post_init(self, __context) -> None:
        if self.source_channel not in VALID_LEAD_SOURCES:
            raise ValueError(f"source_channel must be one of {sorted(VALID_LEAD_SOURCES)}")


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    source_channel: str
    campaign: Optional[str]
    status: str
    assigned_manager_id: Optional[uuid.UUID]
    converted_customer_id: Optional[uuid.UUID]
    created_at: datetime


class LeadListOut(BaseModel):
    items: List[LeadOut]
    next_cursor: Optional[str] = None


class LeadConvertOut(BaseModel):
    customer_id: uuid.UUID
    contact_id: Optional[uuid.UUID]
