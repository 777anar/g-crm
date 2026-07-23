import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.domain.value_objects import RESERVATION_STATUS_ACTIVE
from modules.catalog.infrastructure.models.slab_reservation import SlabReservation


class SlabReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, reservation: SlabReservation) -> SlabReservation:
        self.db.add(reservation)
        self.db.flush()
        return reservation

    def get(self, *, company_id: uuid.UUID, reservation_id: uuid.UUID) -> Optional[SlabReservation]:
        return self.db.scalar(
            select(SlabReservation).where(
                SlabReservation.id == reservation_id, SlabReservation.company_id == company_id
            )
        )

    def get_active_for_slab(self, *, company_id: uuid.UUID, slab_id: uuid.UUID) -> Optional[SlabReservation]:
        return self.db.scalar(
            select(SlabReservation).where(
                SlabReservation.company_id == company_id,
                SlabReservation.slab_id == slab_id,
                SlabReservation.status == RESERVATION_STATUS_ACTIVE,
            )
        )

    def get_active_for_order_item(
        self, *, company_id: uuid.UUID, order_item_id: uuid.UUID
    ) -> Optional[SlabReservation]:
        return self.db.scalar(
            select(SlabReservation).where(
                SlabReservation.company_id == company_id,
                SlabReservation.order_item_id == order_item_id,
                SlabReservation.status == RESERVATION_STATUS_ACTIVE,
            )
        )

    def list_for_order(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> List[SlabReservation]:
        stmt = (
            select(SlabReservation)
            .where(SlabReservation.company_id == company_id, SlabReservation.order_id == order_id)
            .order_by(SlabReservation.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_slab(self, *, company_id: uuid.UUID, slab_id: uuid.UUID) -> List[SlabReservation]:
        stmt = (
            select(SlabReservation)
            .where(SlabReservation.company_id == company_id, SlabReservation.slab_id == slab_id)
            .order_by(SlabReservation.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_company(
        self,
        *,
        company_id: uuid.UUID,
        order_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SlabReservation]:
        """Company-wide reservation browsing (Phase 19) -- `order_id`
        optional (unlike `list_for_order`), so staff can see every active
        reservation across the company, not only ones reached by first
        knowing which order to look at."""
        stmt = select(SlabReservation).where(SlabReservation.company_id == company_id)
        if order_id is not None:
            stmt = stmt.where(SlabReservation.order_id == order_id)
        if status is not None:
            stmt = stmt.where(SlabReservation.status == status)
        stmt = stmt.order_by(SlabReservation.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
