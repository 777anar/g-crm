import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.quote_section import QuoteSection


class SectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, section: QuoteSection) -> QuoteSection:
        self.db.add(section)
        self.db.flush()
        return section

    def get(self, *, company_id: uuid.UUID, section_id: uuid.UUID) -> Optional[QuoteSection]:
        return self.db.scalar(
            select(QuoteSection).where(
                QuoteSection.id == section_id, QuoteSection.company_id == company_id
            )
        )

    def list_for_quote(self, *, company_id: uuid.UUID, quote_id: uuid.UUID) -> List[QuoteSection]:
        stmt = (
            select(QuoteSection)
            .where(QuoteSection.company_id == company_id, QuoteSection.quote_id == quote_id)
            .order_by(QuoteSection.sort_order.asc(), QuoteSection.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, section: QuoteSection) -> None:
        self.db.delete(section)
        self.db.flush()
