from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreateSlabInput, UpdateSlabStatusInput
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.exceptions import (
    DuplicateSlabNumberError,
    InvalidSlabTransitionError,
    SlabStatusRequiresSystemActionError,
)
from modules.catalog.domain.value_objects import (
    DEFAULT_SLAB_STATUS,
    RESERVATION_STATUS_RELEASED,
    SLAB_STATUS_SCRAP,
    SLAB_STATUS_SOLD,
    SYSTEM_ONLY_SLAB_STATUSES,
    is_valid_slab_transition,
)
from modules.catalog.infrastructure.models.slab import Slab
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository
from modules.catalog.infrastructure.repositories.slab_repository import SlabRepository
from modules.catalog.infrastructure.repositories.slab_reservation_repository import SlabReservationRepository
from modules.catalog.infrastructure.repositories.warehouse_repository import WarehouseRepository

MODULE_NAME = "catalog"


class CreateSlabUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.slabs = SlabRepository(db)
        self.materials = MaterialRepository(db)
        self.warehouses = WarehouseRepository(db)

    def execute(self, data: CreateSlabInput) -> Slab:
        if self.materials.get(company_id=data.company_id, material_id=data.material_id) is None:
            raise NotFoundError("Material not found")
        if self.warehouses.get(company_id=data.company_id, warehouse_id=data.warehouse_id) is None:
            raise NotFoundError("Warehouse not found")
        if self.slabs.get_by_slab_number(company_id=data.company_id, slab_number=data.slab_number) is not None:
            raise DuplicateSlabNumberError(f"Slab number '{data.slab_number}' already exists in this company")

        area_m2 = None
        if data.length_mm is not None and data.width_mm is not None:
            area_m2 = (data.length_mm * data.width_mm) / Decimal("1000000")

        slab = Slab(
            company_id=data.company_id,
            material_id=data.material_id,
            warehouse_id=data.warehouse_id,
            slab_number=data.slab_number,
            lot_number=data.lot_number,
            barcode=data.barcode,
            rack_location=data.rack_location,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            area_m2=area_m2,
            weight_kg=data.weight_kg,
            status=data.status or DEFAULT_SLAB_STATUS,
            created_by=data.actor_user_id,
            parent_slab_id=data.parent_slab_id,
            is_offcut=data.is_offcut,
            image_document_id=data.image_document_id,
        )
        self.slabs.add(slab)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="slab.created",
            entity_type="slab",
            entity_id=slab.id,
            diff={"slab_number": slab.slab_number, "material_id": str(slab.material_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.SLAB_CREATED,
                company_id=data.company_id,
                payload={"slab_id": str(slab.id), "slab_number": slab.slab_number, "material_id": str(slab.material_id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return slab


class UpdateSlabStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.slabs = SlabRepository(db)
        self.reservations = SlabReservationRepository(db)

    def execute(self, data: UpdateSlabStatusInput) -> Slab:
        slab = self.slabs.get(company_id=data.company_id, slab_id=data.slab_id)
        if slab is None:
            raise NotFoundError("Slab not found")

        if not is_valid_slab_transition(current=slab.status, target=data.status):
            raise InvalidSlabTransitionError(f"Cannot move slab from '{slab.status}' to '{data.status}'")

        if data.status in SYSTEM_ONLY_SLAB_STATUSES and not data.system_triggered:
            raise SlabStatusRequiresSystemActionError(
                f"'{data.status}' can only be reached automatically (e.g. by completing the "
                "production work order using this slab), not set directly"
            )

        old_status = slab.status
        slab.status = data.status

        # A user manually selling or scrapping a slab that was still
        # `reserved`/`in_production` for a specific order item must not
        # leave that reservation dangling `active` forever (Phase 19's
        # sold/consumed data-quality fix). `consumed` is excluded here since
        # Production's own cascade already releases/consumes the
        # reservation itself (`_cascade_reservations`), keyed by
        # order_item_id rather than slab status -- and `offcut_created`
        # (via `CreateOffcutUseCase`, which doesn't go through this use
        # case) deliberately leaves an in-progress reservation alone too:
        # the parent slab going terminal mid-job doesn't mean the order
        # item it was reserved for is done, so that same cascade still
        # needs to find and consume it once the work order completes.
        if data.status in {SLAB_STATUS_SOLD, SLAB_STATUS_SCRAP} and old_status != data.status:
            self._release_dangling_reservation(data)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="slab.status_changed",
            entity_type="slab",
            entity_id=slab.id,
            diff={"status": {"old": old_status, "new": slab.status}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.SLAB_STATUS_CHANGED,
                company_id=data.company_id,
                payload={"slab_id": str(slab.id), "old_status": old_status, "new_status": slab.status},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return slab

    def _release_dangling_reservation(self, data: UpdateSlabStatusInput) -> None:
        reservation = self.reservations.get_active_for_slab(company_id=data.company_id, slab_id=data.slab_id)
        if reservation is None:
            return
        reservation.status = RESERVATION_STATUS_RELEASED
        reservation.released_at = datetime.now(timezone.utc)
        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="slab_reservation.released",
            entity_type="slab_reservation",
            entity_id=reservation.id,
            diff={"slab_id": str(data.slab_id), "reason": f"slab_status_changed_to_{data.status}"},
        )
        event_bus.publish(
            Event(
                name=catalog_events.SLAB_RESERVATION_RELEASED,
                company_id=data.company_id,
                payload={"reservation_id": str(reservation.id), "slab_id": str(data.slab_id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
