import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_number_sequence import QuoteNumberSequence


class QuoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, quote: Quote) -> Quote:
        self.db.add(quote)
        self.db.flush()
        return quote

    def get(self, *, company_id: uuid.UUID, quote_id: uuid.UUID) -> Optional[Quote]:
        return self.db.scalar(
            select(Quote).where(Quote.id == quote_id, Quote.company_id == company_id)
        )

    def list_for_project(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> List[Quote]:
        stmt = (
            select(Quote)
            .where(Quote.company_id == company_id, Quote.project_id == project_id)
            .order_by(Quote.version.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list(
        self,
        *,
        company_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Quote]:
        stmt = select(Quote).where(Quote.company_id == company_id)
        if customer_id:
            stmt = stmt.where(Quote.customer_id == customer_id)
        if project_id:
            stmt = stmt.where(Quote.project_id == project_id)
        if status:
            stmt = stmt.where(Quote.status == status)
        stmt = stmt.order_by(Quote.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_max_version(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = self.db.scalar(
            select(func.max(Quote.version)).where(
                Quote.company_id == company_id, Quote.project_id == project_id
            )
        )
        return result or 0

    def next_quote_number(self, *, company_id: uuid.UUID, year: int) -> str:
        """Atomically increments the per-company-per-year counter and returns
        a formatted quote number like 'QT-2026-0001'."""
        seq = self.db.scalar(
            select(QuoteNumberSequence).where(
                QuoteNumberSequence.company_id == company_id,
                QuoteNumberSequence.year == year,
            )
        )
        if seq is None:
            seq = QuoteNumberSequence(company_id=company_id, year=year, last_number=0)
            self.db.add(seq)
            self.db.flush()
        seq.last_number += 1
        self.db.flush()
        return f"QT-{year}-{seq.last_number:04d}"
