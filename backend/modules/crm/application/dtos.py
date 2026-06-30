"""Application-layer input DTOs. Presentation schemas (Pydantic, HTTP-shaped)
map onto these before calling a use-case, keeping the use-case layer free of
any FastAPI/Pydantic import."""
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CreateCustomerInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    name: str
    type: str
    assigned_manager_id: Optional[uuid.UUID] = None
    lead_source: Optional[str] = None
    advertising_campaign: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    contact_full_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


@dataclass
class UpdateCustomerInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    customer_id: uuid.UUID
    name: Optional[str] = None
    assigned_manager_id: Optional[uuid.UUID] = None
    lead_source: Optional[str] = None
    advertising_campaign: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class ArchiveCustomerInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    customer_id: uuid.UUID


@dataclass
class AddCustomerNoteInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    customer_id: uuid.UUID
    body: str


@dataclass
class CreateLeadInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    full_name: str
    source_channel: str
    email: Optional[str] = None
    phone: Optional[str] = None
    campaign: Optional[str] = None
    assigned_manager_id: Optional[uuid.UUID] = None


@dataclass
class ConvertLeadInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    lead_id: uuid.UUID
