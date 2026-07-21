"""Application-layer input DTOs. Presentation schemas (Pydantic, HTTP-shaped)
map onto these before calling a use-case, keeping the use-case layer free of
any FastAPI/Pydantic import."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
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
    type: Optional[str] = None
    assigned_manager_id: Optional[uuid.UUID] = None
    clear_assigned_manager: bool = False
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
    campaign_id: Optional[uuid.UUID] = None
    assigned_manager_id: Optional[uuid.UUID] = None


@dataclass
class ConvertLeadInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    lead_id: uuid.UUID


@dataclass
class CreateTaskInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    remind_at: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None
    tags: List[str] = field(default_factory=list)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[uuid.UUID] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    recurrence_interval: int = 1
    recurrence_end_date: Optional[str] = None


@dataclass
class UpdateTaskInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    task_id: uuid.UUID
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


@dataclass
class UpdateTaskStatusInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    task_id: uuid.UUID
    status: str
    cancelled_reason: Optional[str] = None


@dataclass
class DeleteTaskInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    task_id: uuid.UUID


@dataclass
class GenerateDueTaskNotificationsInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class MarkTaskNotificationReadInput:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID
    notification_id: uuid.UUID
