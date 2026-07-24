import uuid
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.ai.infrastructure.models.provider_call_log import AIProviderCallLog


class AIProviderCallLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, log: AIProviderCallLog) -> AIProviderCallLog:
        self.db.add(log)
        self.db.flush()
        return log

    def list(
        self, *, company_id: uuid.UUID, limit: int = 25, offset: int = 0
    ) -> List[AIProviderCallLog]:
        stmt = (
            select(AIProviderCallLog)
            .where(AIProviderCallLog.company_id == company_id)
            .order_by(AIProviderCallLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def total_cost_since(self, *, company_id: uuid.UUID, since: datetime) -> Decimal:
        stmt = select(func.coalesce(func.sum(AIProviderCallLog.cost_usd), 0)).where(
            AIProviderCallLog.company_id == company_id,
            AIProviderCallLog.created_at >= since,
        )
        return Decimal(str(self.db.scalar(stmt) or 0))

    def total_cost_today(self, *, company_id: uuid.UUID) -> Decimal:
        today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        return self.total_cost_since(company_id=company_id, since=today_start)

    def call_count_today(self, *, company_id: uuid.UUID) -> int:
        today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        stmt = select(func.count(AIProviderCallLog.id)).where(
            AIProviderCallLog.company_id == company_id,
            AIProviderCallLog.created_at >= today_start,
        )
        return self.db.scalar(stmt) or 0
