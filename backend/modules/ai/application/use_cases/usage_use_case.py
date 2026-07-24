"""Phase 21 cost-control visibility: today's spend/call count against this
company's configured daily budget, plus a recent call log page -- the
operational counterpart to the enforcement in `_shared.py`'s
`_check_usage_allowed`, so an admin can see why a request was rejected (or
that spend is approaching the cap) rather than only experiencing the 429.
"""
from typing import List

from sqlalchemy.orm import Session

from core.config import settings
from modules.ai.application.dtos import GetAIUsageInput
from modules.ai.infrastructure.models.provider_call_log import AIProviderCallLog
from modules.ai.infrastructure.repositories.provider_call_log_repository import AIProviderCallLogRepository


class GetAIUsageUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AIProviderCallLogRepository(db)

    def execute(self, data: GetAIUsageInput) -> dict:
        spent_today = self.repo.total_cost_today(company_id=data.company_id)
        calls_today = self.repo.call_count_today(company_id=data.company_id)
        recent: List[AIProviderCallLog] = self.repo.list(
            company_id=data.company_id, limit=data.limit, offset=data.offset
        )
        return {
            "daily_budget_usd": settings.ai_daily_budget_usd,
            "spent_today_usd": spent_today,
            "calls_today": calls_today,
            "budget_remaining_usd": (
                max(settings.ai_daily_budget_usd - float(spent_today), 0.0)
                if settings.ai_daily_budget_usd > 0
                else None
            ),
            "recent_calls": recent,
        }
