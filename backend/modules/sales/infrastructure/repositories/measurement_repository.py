import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.quote_section_measurement import QuoteSectionMeasurement


class MeasurementRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, m: QuoteSectionMeasurement) -> QuoteSectionMeasurement:
        self.db.add(m)
        self.db.flush()
        return m

    def get(self, *, company_id: uuid.UUID, measurement_id: uuid.UUID) -> Optional[QuoteSectionMeasurement]:
        return self.db.scalar(
            select(QuoteSectionMeasurement).where(
                QuoteSectionMeasurement.id == measurement_id,
                QuoteSectionMeasurement.company_id == company_id,
            )
        )

    def list_for_section(self, *, company_id: uuid.UUID, section_id: uuid.UUID) -> List[QuoteSectionMeasurement]:
        stmt = (
            select(QuoteSectionMeasurement)
            .where(
                QuoteSectionMeasurement.company_id == company_id,
                QuoteSectionMeasurement.section_id == section_id,
            )
            .order_by(QuoteSectionMeasurement.sort_order.asc(), QuoteSectionMeasurement.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_quote(self, *, company_id: uuid.UUID, quote_id: uuid.UUID) -> List[QuoteSectionMeasurement]:
        stmt = (
            select(QuoteSectionMeasurement)
            .where(
                QuoteSectionMeasurement.company_id == company_id,
                QuoteSectionMeasurement.quote_id == quote_id,
            )
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, m: QuoteSectionMeasurement) -> None:
        self.db.delete(m)
        self.db.flush()
