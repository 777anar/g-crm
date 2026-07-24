import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AIProviderCallLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_kind: str
    provider: str
    model: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost_usd: Optional[Decimal]
    latency_ms: int
    success: bool
    error_message: Optional[str]
    created_at: datetime


class AIUsageOut(BaseModel):
    daily_budget_usd: float
    spent_today_usd: Decimal
    calls_today: int
    budget_remaining_usd: Optional[float]
    recent_calls: List[AIProviderCallLogOut]
