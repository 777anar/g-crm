import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from modules.sales.domain.value_objects import VALID_DRAWING_TYPES


class ProjectItemDrawingCreate(BaseModel):
    document_id: uuid.UUID
    drawing_type: str = "sketch"
    label: Optional[str] = None
    sort_order: int = 0

    def model_post_init(self, __context):
        if self.drawing_type not in VALID_DRAWING_TYPES:
            raise ValueError(f"Invalid drawing_type: {self.drawing_type}")


class ProjectItemDrawingOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    project_item_id: uuid.UUID
    document_id: uuid.UUID
    drawing_type: str
    label: Optional[str]
    sort_order: int
    uploaded_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectItemDrawingListOut(BaseModel):
    items: List[ProjectItemDrawingOut]
