import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from modules.crm.domain.value_objects import VALID_CUSTOMER_TYPES


class ContactCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerCreate(BaseModel):
    name: str
    type: str = Field(default="individual")
    assigned_manager_id: Optional[uuid.UUID] = None
    lead_source: Optional[str] = None
    advertising_campaign: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    contact: Optional[ContactCreate] = None

    def model_post_init(self, __context) -> None:
        if self.type not in VALID_CUSTOMER_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_CUSTOMER_TYPES)}")


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    assigned_manager_id: Optional[uuid.UUID] = None
    lead_source: Optional[str] = None
    advertising_campaign: Optional[str] = None
    tags: Optional[List[str]] = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str
    primary_contact_id: Optional[uuid.UUID]
    assigned_manager_id: Optional[uuid.UUID]
    lead_source: Optional[str]
    advertising_campaign: Optional[str]
    tags: List[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    @property
    def is_archived(self) -> bool:
        return self.deleted_at is not None


class CustomerListOut(BaseModel):
    items: List[CustomerOut]
    next_cursor: Optional[str] = None


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: Optional[str]
    phone: Optional[str]


class AddNoteRequest(BaseModel):
    body: str


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    body: str
    created_by: uuid.UUID
    created_at: datetime


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_path: str
    mime_type: str
    created_at: datetime


class CustomerProfileOut(BaseModel):
    customer: CustomerOut
    contacts: List[ContactOut]
    attachments: List[AttachmentOut]
    timeline: List[ActivityOut]
    projects: List[dict] = Field(default_factory=list)
    quotes: List[dict] = Field(default_factory=list)
    orders: List[dict] = Field(default_factory=list)
    payments: List[dict] = Field(default_factory=list)
