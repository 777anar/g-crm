"""Application-layer input DTOs. Presentation schemas (Pydantic) map onto
these before calling a use-case, keeping the use-case layer free of any
FastAPI/Pydantic import -- same pattern as every other module."""
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class CreateCampaignInput(ActorContext):
    name: str
    channel: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[Decimal] = None
    currency: str = "AZN"
    notes: Optional[str] = None


@dataclass
class UpdateCampaignInput(ActorContext):
    campaign_id: uuid.UUID
    name: Optional[str] = None
    channel: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[Decimal] = None
    notes: Optional[str] = None


@dataclass
class UpdateCampaignStatusInput(ActorContext):
    campaign_id: uuid.UUID
    status: str


@dataclass
class GetCampaignPerformanceInput(ActorContext):
    campaign_id: uuid.UUID
