from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreateWarehouseInput, UpdateWarehouseInput
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS
from modules.catalog.infrastructure.models.warehouse import Warehouse
from modules.catalog.infrastructure.repositories.warehouse_repository import WarehouseRepository

MODULE_NAME = "catalog"


class CreateWarehouseUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.warehouses = WarehouseRepository(db)

    def execute(self, data: CreateWarehouseInput) -> Warehouse:
        warehouse = Warehouse(
            company_id=data.company_id,
            name=data.name,
            address=data.address,
            status=DEFAULT_ENTITY_STATUS,
            created_by=data.actor_user_id,
        )
        self.warehouses.add(warehouse)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="warehouse.created",
            entity_type="warehouse",
            entity_id=warehouse.id,
            diff={"name": warehouse.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.WAREHOUSE_CREATED,
                company_id=data.company_id,
                payload={"warehouse_id": str(warehouse.id), "name": warehouse.name},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return warehouse


class UpdateWarehouseUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.warehouses = WarehouseRepository(db)

    def execute(self, data: UpdateWarehouseInput) -> Warehouse:
        warehouse = self.warehouses.get(company_id=data.company_id, warehouse_id=data.warehouse_id)
        if warehouse is None:
            raise NotFoundError("Warehouse not found")

        diff = {}
        for field_name in ("name", "address", "status"):
            new_value = getattr(data, field_name)
            if new_value is not None and new_value != getattr(warehouse, field_name):
                diff[field_name] = {"old": getattr(warehouse, field_name), "new": new_value}
                setattr(warehouse, field_name, new_value)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="warehouse.updated",
            entity_type="warehouse",
            entity_id=warehouse.id,
            diff=diff,
        )
        self.db.flush()
        return warehouse
