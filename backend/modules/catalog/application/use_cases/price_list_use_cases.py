from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreatePriceListInput, UpsertPriceListEntryInput
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS
from modules.catalog.infrastructure.models.price_list import PriceList, PriceListEntry
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository
from modules.catalog.infrastructure.repositories.price_list_repository import (
    PriceListEntryRepository,
    PriceListRepository,
)

MODULE_NAME = "catalog"


class CreatePriceListUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.price_lists = PriceListRepository(db)

    def execute(self, data: CreatePriceListInput) -> PriceList:
        price_list = PriceList(
            company_id=data.company_id,
            name=data.name,
            currency=data.currency,
            is_default=data.is_default,
            status=DEFAULT_ENTITY_STATUS,
            created_by=data.actor_user_id,
        )
        self.price_lists.add(price_list)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="price_list.created",
            entity_type="price_list",
            entity_id=price_list.id,
            diff={"name": price_list.name, "currency": price_list.currency},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.PRICE_LIST_CREATED,
                company_id=data.company_id,
                payload={"price_list_id": str(price_list.id), "name": price_list.name},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return price_list


class UpsertPriceListEntryUseCase:
    """Sets a Material's cost/sale price within a PriceList. "Upsert" because
    a price list naturally evolves one material at a time -- re-submitting
    the same material updates its existing entry rather than erroring."""

    def __init__(self, db: Session):
        self.db = db
        self.price_lists = PriceListRepository(db)
        self.materials = MaterialRepository(db)
        self.entries = PriceListEntryRepository(db)

    def execute(self, data: UpsertPriceListEntryInput) -> PriceListEntry:
        if self.price_lists.get(company_id=data.company_id, price_list_id=data.price_list_id) is None:
            raise NotFoundError("Price list not found")
        if self.materials.get(company_id=data.company_id, material_id=data.material_id) is None:
            raise NotFoundError("Material not found")

        existing = self.entries.get_for_material(
            company_id=data.company_id, price_list_id=data.price_list_id, material_id=data.material_id
        )
        action = "price_list_entry.updated" if existing else "price_list_entry.created"

        if existing:
            entry = existing
            entry.cost_price = data.cost_price
            entry.sale_price = data.sale_price
        else:
            entry = PriceListEntry(
                company_id=data.company_id,
                price_list_id=data.price_list_id,
                material_id=data.material_id,
                cost_price=data.cost_price,
                sale_price=data.sale_price,
            )
            self.entries.add(entry)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action=action,
            entity_type="price_list_entry",
            entity_id=entry.id,
            diff={"cost_price": str(entry.cost_price), "sale_price": str(entry.sale_price)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.PRICE_LIST_ENTRY_UPSERTED,
                company_id=data.company_id,
                payload={
                    "price_list_id": str(data.price_list_id),
                    "material_id": str(data.material_id),
                    "sale_price": str(entry.sale_price),
                },
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return entry
