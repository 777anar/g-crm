import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.orders.infrastructure.models.order_measurement import OrderMeasurement


class OrderMeasurementRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, measurement: OrderMeasurement) -> OrderMeasurement:
        self.db.add(measurement)
        self.db.flush()
        return measurement

    def list_for_order(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> List[OrderMeasurement]:
        stmt = (
            select(OrderMeasurement)
            .where(OrderMeasurement.company_id == company_id, OrderMeasurement.order_id == order_id)
            .order_by(OrderMeasurement.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_section(self, *, company_id: uuid.UUID, section_id: uuid.UUID) -> List[OrderMeasurement]:
        stmt = (
            select(OrderMeasurement)
            .where(OrderMeasurement.company_id == company_id, OrderMeasurement.section_id == section_id)
            .order_by(OrderMeasurement.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())
