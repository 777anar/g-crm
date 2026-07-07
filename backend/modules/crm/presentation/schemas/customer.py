import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from modules.crm.domain.value_objects import (
    DEFAULT_CUSTOMER_STATUS,
    VALID_CUSTOMER_STATUSES,
    VALID_CUSTOMER_TYPES,
    VALID_LEAD_SOURCES,
)


class ContactCreate(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class CustomerCreate(BaseModel):
    name: str
    type: str = Field(default="individual")
    assigned_manager_id: Optional[uuid.UUID] = None
    lead_source: Optional[str] = None
    advertising_campaign: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None
    status: str = Field(default=DEFAULT_CUSTOMER_STATUS)
    tags: List[str] = Field(default_factory=list)
    contact: Optional[ContactCreate] = None

    def model_post_init(self, __context) -> None:
        if self.type not in VALID_CUSTOMER_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_CUSTOMER_TYPES)}")
        if self.lead_source is not None and self.lead_source not in VALID_LEAD_SOURCES:
            raise ValueError(f"lead_source must be one of {sorted(VALID_LEAD_SOURCES)}")
        if self.status not in VALID_CUSTOMER_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_CUSTOMER_STATUSES)}")


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    assigned_manager_id: Optional[uuid.UUID] = None
    lead_source: Optional[str] = None
    advertising_campaign: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

    def model_post_init(self, __context) -> None:
        if self.lead_source is not None and self.lead_source not in VALID_LEAD_SOURCES:
            raise ValueError(f"lead_source must be one of {sorted(VALID_LEAD_SOURCES)}")
        if self.status is not None and self.status not in VALID_CUSTOMER_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_CUSTOMER_STATUSES)}")


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str
    primary_contact_id: Optional[uuid.UUID]
    assigned_manager_id: Optional[uuid.UUID]
    lead_source: Optional[str]
    advertising_campaign: Optional[str]
    phone: Optional[str]
    whatsapp: Optional[str]
    instagram: Optional[str]
    facebook: Optional[str]
    email: Optional[str]
    address: Optional[str]
    company_name: Optional[str]
    notes: Optional[str]
    status: str
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
