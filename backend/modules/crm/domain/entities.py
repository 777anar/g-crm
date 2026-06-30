"""Domain entities: pure business logic, no SQLAlchemy/FastAPI imports.
Infrastructure models are a separate, persistence-shaped representation;
mapping between the two happens in the repositories."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from modules.crm.domain.exceptions import CustomerAlreadyArchivedError, LeadAlreadyConvertedError
from modules.crm.domain.value_objects import LEAD_STATUS_CONVERTED


@dataclass
class Customer:
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    type: str
    primary_contact_id: Optional[uuid.UUID]
    assigned_manager_id: Optional[uuid.UUID]
    lead_source: Optional[str]
    advertising_campaign: Optional[str]
    tags: List[str] = field(default_factory=list)
    created_by: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @property
    def is_archived(self) -> bool:
        return self.deleted_at is not None

    def archive(self, *, at: datetime) -> None:
        if self.is_archived:
            raise CustomerAlreadyArchivedError(f"Customer {self.id} is already archived")
        self.deleted_at = at


@dataclass
class Lead:
    id: uuid.UUID
    company_id: uuid.UUID
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    source_channel: str
    campaign: Optional[str]
    status: str
    assigned_manager_id: Optional[uuid.UUID]
    converted_customer_id: Optional[uuid.UUID] = None
    converted_contact_id: Optional[uuid.UUID] = None
    converted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_converted(self) -> bool:
        return self.status == LEAD_STATUS_CONVERTED

    def mark_converted(self, *, customer_id: uuid.UUID, contact_id: uuid.UUID, at: datetime) -> None:
        if self.is_converted:
            raise LeadAlreadyConvertedError(f"Lead {self.id} has already been converted")
        self.status = LEAD_STATUS_CONVERTED
        self.converted_customer_id = customer_id
        self.converted_contact_id = contact_id
        self.converted_at = at
