import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.installation.domain.value_objects import VALID_JOB_STATUSES, VALID_PHOTO_TYPES


class InstallationJobCreate(BaseModel):
    order_id: uuid.UUID


class InstallationJobUpdate(BaseModel):
    crew_id: Optional[uuid.UUID] = None
    scheduled_date: Optional[str] = None
    scheduled_time_slot: Optional[str] = None
    route_sequence: Optional[int] = None
    notes: Optional[str] = None


class InstallationJobStatusUpdate(BaseModel):
    status: str
    cancelled_reason: Optional[str] = None
    completion_notes: Optional[str] = None

    def model_post_init(self, __context):
        if self.status not in VALID_JOB_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")


class InstallationJobOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_id: uuid.UUID
    job_number: str
    status: str
    crew_id: Optional[uuid.UUID]
    scheduled_date: Optional[str]
    scheduled_time_slot: Optional[str]
    route_sequence: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_reason: Optional[str]
    notes: Optional[str]
    completion_notes: Optional[str]
    signature_status: Optional[str] = None
    signature_provider: Optional[str] = None
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InstallationJobListOut(BaseModel):
    items: List[InstallationJobOut]
    next_cursor: Optional[str] = None


class RequestJobSignatureRequest(BaseModel):
    provider: Optional[str] = None


class SimulateJobSignatureRequest(BaseModel):
    outcome: str  # "completed" | "declined"


class InstallationPhotoCreate(BaseModel):
    document_id: uuid.UUID
    photo_type: str
    caption: Optional[str] = None
    sort_order: int = 0

    def model_post_init(self, __context):
        if self.photo_type not in VALID_PHOTO_TYPES:
            raise ValueError(f"Invalid photo_type: {self.photo_type}")


class InstallationPhotoOut(BaseModel):
    id: uuid.UUID
    installation_job_id: uuid.UUID
    document_id: uuid.UUID
    photo_type: str
    caption: Optional[str]
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InstallationPhotoListOut(BaseModel):
    items: List[InstallationPhotoOut]
