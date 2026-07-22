"""Material Reservation + offcut tracking (Phase 1 of the Purchasing ->
Inventory -> Production stone-fabrication workflow).

Reservation is deliberately a separate, durable record from Slab.status:
the status alone tells you a slab *is* reserved, never for whom, so two
badly-timed reservation attempts against the same slab would only be
caught by re-reading status at the last moment. `SlabReservation` gives a
real row to conflict against (checked-and-set inside one use case
execution, the same "no partial unique index, just an in-transaction
check" pattern already used for PO-number sequences and Sales' own
quote-acceptance slab check) plus a queryable history of who reserved what,
for whom, and when.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import (
    ConsumeSlabReservationInput,
    CreateOffcutInput,
    CreateSlabInput,
    CreateSlabReservationInput,
    ReleaseSlabReservationInput,
    UpdateSlabStatusInput,
)
from modules.catalog.application.use_cases.slab_use_cases import CreateSlabUseCase, UpdateSlabStatusUseCase
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.exceptions import SlabAlreadyReservedError, SlabNotInProductionError, SlabNotReservableError
from modules.catalog.domain.value_objects import (
    RESERVATION_STATUS_ACTIVE,
    RESERVATION_STATUS_CONSUMED,
    RESERVATION_STATUS_RELEASED,
    SLAB_STATUS_AVAILABLE,
    SLAB_STATUS_IN_PRODUCTION,
    SLAB_STATUS_OFFCUT_CREATED,
    SLAB_STATUS_RESERVED,
)
from modules.catalog.infrastructure.models.slab_reservation import SlabReservation
from modules.catalog.infrastructure.repositories.slab_repository import SlabRepository
from modules.catalog.infrastructure.repositories.slab_reservation_repository import SlabReservationRepository

MODULE_NAME = "catalog"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateSlabReservationUseCase:
    """Reserves a slab for a specific order item. Idempotent when called
    again for the exact same order item (returns the existing active
    reservation unchanged); raises SlabAlreadyReservedError when the slab
    is already actively reserved for a *different* order item -- the
    double-booking guard.

    `require_available=False` (used when Orders adopts a reservation that
    already happened implicitly at quote-acceptance time) skips both the
    availability check and the slab-status transition, since the slab is
    already known to be `reserved` -- it only records the bookkeeping row.
    """

    def __init__(self, db: Session):
        self.db = db
        self.slabs = SlabRepository(db)
        self.reservations = SlabReservationRepository(db)

    def execute(self, data: CreateSlabReservationInput) -> SlabReservation:
        slab = self.slabs.get(company_id=data.company_id, slab_id=data.slab_id)
        if slab is None:
            raise NotFoundError("Slab not found")

        existing = self.reservations.get_active_for_slab(company_id=data.company_id, slab_id=data.slab_id)
        if existing is not None:
            if str(existing.order_item_id) == str(data.order_item_id):
                return existing
            raise SlabAlreadyReservedError(
                f"Slab '{slab.slab_number}' is already reserved for another order item"
            )

        if data.require_available and slab.status != SLAB_STATUS_AVAILABLE:
            raise SlabNotReservableError(
                f"Slab '{slab.slab_number}' cannot be reserved from status '{slab.status}' "
                f"(must be '{SLAB_STATUS_AVAILABLE}')"
            )

        reservation = SlabReservation(
            company_id=data.company_id,
            slab_id=data.slab_id,
            order_id=data.order_id,
            order_item_id=data.order_item_id,
            status=RESERVATION_STATUS_ACTIVE,
            notes=data.notes,
            reserved_by=data.actor_user_id,
            reserved_at=_now(),
        )
        self.reservations.add(reservation)

        if data.require_available:
            UpdateSlabStatusUseCase(self.db).execute(
                UpdateSlabStatusInput(
                    company_id=data.company_id,
                    actor_user_id=data.actor_user_id,
                    slab_id=data.slab_id,
                    status=SLAB_STATUS_RESERVED,
                )
            )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="slab_reservation.created",
            entity_type="slab_reservation",
            entity_id=reservation.id,
            diff={"slab_id": str(data.slab_id), "order_id": str(data.order_id), "order_item_id": str(data.order_item_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.SLAB_RESERVATION_CREATED,
                company_id=data.company_id,
                payload={
                    "reservation_id": str(reservation.id),
                    "slab_id": str(data.slab_id),
                    "order_id": str(data.order_id),
                    "order_item_id": str(data.order_item_id),
                },
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return reservation


class ReleaseSlabReservationUseCase:
    """Releases an active reservation and, if the slab is still `reserved`
    (not already moved on to in_production/consumed/etc. by something
    else), returns it to `available`."""

    def __init__(self, db: Session):
        self.db = db
        self.slabs = SlabRepository(db)
        self.reservations = SlabReservationRepository(db)

    def execute(self, data: ReleaseSlabReservationInput) -> SlabReservation:
        reservation = self.reservations.get(company_id=data.company_id, reservation_id=data.reservation_id)
        if reservation is None:
            raise NotFoundError("Reservation not found")

        reservation.status = RESERVATION_STATUS_RELEASED
        reservation.released_at = _now()

        slab = self.slabs.get(company_id=data.company_id, slab_id=uuid.UUID(str(reservation.slab_id)))
        if slab is not None and slab.status == SLAB_STATUS_RESERVED:
            UpdateSlabStatusUseCase(self.db).execute(
                UpdateSlabStatusInput(
                    company_id=data.company_id,
                    actor_user_id=data.actor_user_id,
                    slab_id=slab.id,
                    status=SLAB_STATUS_AVAILABLE,
                )
            )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="slab_reservation.released",
            entity_type="slab_reservation",
            entity_id=reservation.id,
            diff={"slab_id": str(reservation.slab_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.SLAB_RESERVATION_RELEASED,
                company_id=data.company_id,
                payload={"reservation_id": str(reservation.id), "slab_id": str(reservation.slab_id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return reservation


class ConsumeSlabReservationUseCase:
    """Marks the active reservation for an order item as consumed --
    called by Production when the work order carrying that item
    completes. A no-op (returns None) if no active reservation exists,
    since not every slab-linked item necessarily has one yet."""

    def __init__(self, db: Session):
        self.db = db
        self.reservations = SlabReservationRepository(db)

    def execute(self, data: ConsumeSlabReservationInput) -> Optional[SlabReservation]:
        reservation = self.reservations.get_active_for_order_item(
            company_id=data.company_id, order_item_id=data.order_item_id
        )
        if reservation is None:
            return None

        reservation.status = RESERVATION_STATUS_CONSUMED
        reservation.released_at = _now()
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.SLAB_RESERVATION_CONSUMED,
                company_id=data.company_id,
                payload={"reservation_id": str(reservation.id), "slab_id": str(reservation.slab_id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return reservation


class CreateOffcutUseCase:
    """Registers a remnant piece cut from a slab that's actively
    `in_production` as its own independently reservable Slab row (same
    material/warehouse, a new slab_number, `is_offcut=True`, status
    `available`), and moves the *parent* slab to the terminal
    `offcut_created` status -- distinct from `consumed` (fully used, no
    remnant) so inventory reports can tell the two outcomes apart."""

    def __init__(self, db: Session):
        self.db = db
        self.slabs = SlabRepository(db)

    def execute(self, data: CreateOffcutInput):
        parent = self.slabs.get(company_id=data.company_id, slab_id=data.parent_slab_id)
        if parent is None:
            raise NotFoundError("Parent slab not found")
        if parent.status != SLAB_STATUS_IN_PRODUCTION:
            raise SlabNotInProductionError(
                f"Slab '{parent.slab_number}' must be '{SLAB_STATUS_IN_PRODUCTION}' to register an offcut "
                f"from it (current status: '{parent.status}')"
            )

        offcut = CreateSlabUseCase(self.db).execute(
            CreateSlabInput(
                company_id=data.company_id,
                actor_user_id=data.actor_user_id,
                material_id=uuid.UUID(str(parent.material_id)),
                warehouse_id=data.warehouse_id,
                slab_number=data.slab_number,
                length_mm=data.length_mm,
                width_mm=data.width_mm,
                weight_kg=data.weight_kg,
                parent_slab_id=parent.id,
                is_offcut=True,
            )
        )

        old_status = parent.status
        parent.status = SLAB_STATUS_OFFCUT_CREATED

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="slab.offcut_created",
            entity_type="slab",
            entity_id=parent.id,
            diff={"offcut_slab_id": str(offcut.id), "offcut_slab_number": offcut.slab_number},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.SLAB_STATUS_CHANGED,
                company_id=data.company_id,
                payload={"slab_id": str(parent.id), "old_status": old_status, "new_status": parent.status},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        event_bus.publish(
            Event(
                name=catalog_events.SLAB_OFFCUT_CREATED,
                company_id=data.company_id,
                payload={"parent_slab_id": str(parent.id), "offcut_slab_id": str(offcut.id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return offcut
