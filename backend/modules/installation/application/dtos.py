"""Application-layer input DTOs for the Installation module."""
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateCrewInput(ActorContext):
    name: str
    notes: Optional[str] = None


@dataclass
class UpdateCrewInput(ActorContext):
    crew_id: uuid.UUID
    name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class AddCrewMemberInput(ActorContext):
    crew_id: uuid.UUID
    user_id: uuid.UUID
    is_lead: bool = False


@dataclass
class RemoveCrewMemberInput(ActorContext):
    crew_id: uuid.UUID
    member_id: uuid.UUID


@dataclass
class CreateInstallationJobInput(ActorContext):
    order_id: uuid.UUID


@dataclass
class UpdateInstallationJobInput(ActorContext):
    job_id: uuid.UUID
    crew_id: Optional[uuid.UUID] = None
    scheduled_date: Optional[str] = None
    scheduled_time_slot: Optional[str] = None
    route_sequence: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class UpdateInstallationJobStatusInput(ActorContext):
    job_id: uuid.UUID
    status: str
    cancelled_reason: Optional[str] = None
    completion_notes: Optional[str] = None


@dataclass
class AddInstallationPhotoInput(ActorContext):
    job_id: uuid.UUID
    document_id: uuid.UUID
    photo_type: str
    caption: Optional[str] = None
    sort_order: int = 0


@dataclass
class MarkNotificationReadInput(ActorContext):
    notification_id: uuid.UUID
