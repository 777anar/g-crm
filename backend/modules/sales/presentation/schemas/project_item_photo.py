import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProjectItemPhotoCreate(BaseModel):
    document_id: uuid.UUID
    caption: Optional[str] = None
    sort_order: int = 0


class ProjectItemPhotoOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_item_id: uuid.UUID
    document_id: uuid.UUID
    caption: Optional[str]
    sort_order: int
    uploaded_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectItemPhotoListOut(BaseModel):
    items: List[ProjectItemPhotoOut]
