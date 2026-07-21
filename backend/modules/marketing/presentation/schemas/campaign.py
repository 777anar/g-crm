import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from modules.marketing.domain.value_objects import VALID_CAMPAIGN_CHANNELS, VALID_CAMPAIGN_STATUSES


class CampaignCreate(BaseModel):
    name: str
    channel: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[Decimal] = None
    currency: str = "AZN"
    notes: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.channel not in VALID_CAMPAIGN_CHANNELS:
            raise ValueError(f"channel must be one of {sorted(VALID_CAMPAIGN_CHANNELS)}")


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[Decimal] = None
    notes: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.channel is not None and self.channel not in VALID_CAMPAIGN_CHANNELS:
            raise ValueError(f"channel must be one of {sorted(VALID_CAMPAIGN_CHANNELS)}")


class CampaignStatusUpdate(BaseModel):
    status: str

    def model_post_init(self, __context) -> None:
        if self.status not in VALID_CAMPAIGN_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_CAMPAIGN_STATUSES)}")


class CampaignOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    channel: str
    status: str
    start_date: Optional[str]
    end_date: Optional[str]
    budget: Optional[Decimal]
    currency: str
    notes: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignListOut(BaseModel):
    items: List[CampaignOut]
    next_cursor: Optional[str] = None


class CampaignPerformanceOut(BaseModel):
    leads_count: int
    converted_count: int
    conversion_rate: float
    attributed_revenue: Decimal
