import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem


class ItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, item: QuoteSectionItem) -> QuoteSectionItem:
        self.db.add(item)
        self.db.flush()
        return item

    def get(self, *, company_id: uuid.UUID, item_id: uuid.UUID) -> Optional[QuoteSectionItem]:
        return self.db.scalar(
            select(QuoteSectionItem).where(
                QuoteSectionItem.id == item_id, QuoteSectionItem.company_id == company_id
            )
        )

    def list_for_section(self, *, company_id: uuid.UUID, section_id: uuid.UUID) -> List[QuoteSectionItem]:
        stmt = (
            select(QuoteSectionItem)
            .where(QuoteSectionItem.company_id == company_id, QuoteSectionItem.section_id == section_id)
            .order_by(QuoteSectionItem.sort_order.asc(), QuoteSectionItem.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_quote(self, *, company_id: uuid.UUID, quote_id: uuid.UUID) -> List[QuoteSectionItem]:
        stmt = select(QuoteSectionItem).where(
            QuoteSectionItem.company_id == company_id, QuoteSectionItem.quote_id == quote_id
        )
        return list(self.db.scalars(stmt).all())

    def list_with_slabs_for_quote(self, *, company_id: uuid.UUID, quote_id: uuid.UUID) -> List[QuoteSectionItem]:
        stmt = select(QuoteSectionItem).where(
            QuoteSectionItem.company_id == company_id,
            QuoteSectionItem.quote_id == quote_id,
            QuoteSectionItem.slab_id.isnot(None),
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, item: QuoteSectionItem) -> None:
        self.db.delete(item)
        self.db.flush()
