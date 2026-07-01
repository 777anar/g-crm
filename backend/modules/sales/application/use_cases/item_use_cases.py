from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from modules.sales.application.dtos import CreateItemInput, UpdateItemInput
from modules.sales.application.totals import recompute_quote, recompute_section
from modules.sales.domain.value_objects import (
    ITEM_TYPE_DEFAULT_UNIT,
    MATERIAL_ITEM_TYPES,
    SERVICE_PRICE_KEYS,
    VALID_ITEM_TYPES,
    VALID_UNITS,
)
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem
from modules.sales.infrastructure.repositories.item_repository import ItemRepository
from modules.sales.infrastructure.repositories.measurement_repository import MeasurementRepository
from modules.sales.infrastructure.repositories.quote_repository import QuoteRepository
from modules.sales.infrastructure.repositories.section_repository import SectionRepository
from modules.sales.infrastructure.repositories.service_price_repository import ServicePriceRepository

MODULE = "sales"


def _sync(db, section):
    items = ItemRepository(db).list_for_section(company_id=section.company_id, section_id=section.id)
    measurements = MeasurementRepository(db).list_for_section(company_id=section.company_id, section_id=section.id)
    recompute_section(section, items, measurements)
    quote = QuoteRepository(db).get(company_id=section.company_id, quote_id=section.quote_id)
    if quote:
        secs = SectionRepository(db).list_for_quote(company_id=quote.company_id, quote_id=quote.id)
        recompute_quote(quote, secs)


class CreateItemUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.sections = SectionRepository(db)
        self.items = ItemRepository(db)
        self.service_prices = ServicePriceRepository(db)

    def execute(self, data: CreateItemInput) -> QuoteSectionItem:
        section = self.sections.get(company_id=data.company_id, section_id=data.section_id)
        if section is None:
            raise NotFoundError("Section not found")

        # Auto-fill unit from item type if not provided.
        unit = data.unit or ITEM_TYPE_DEFAULT_UNIT.get(data.item_type, "unit")

        # Auto-fill prices from company service defaults for service items.
        sale_price = data.unit_sale_price
        cost_price = data.unit_cost_price
        if sale_price == Decimal("0") and data.item_type in SERVICE_PRICE_KEYS:
            key = SERVICE_PRICE_KEYS[data.item_type]
            sp = self.service_prices.get(company_id=data.company_id, service_key=key)
            if sp:
                sale_price = Decimal(str(sp.sale_price))
                cost_price = Decimal(str(sp.cost_price))

        qty = Decimal(str(data.quantity))
        item = QuoteSectionItem(
            company_id=data.company_id,
            section_id=data.section_id,
            quote_id=section.quote_id,
            item_type=data.item_type,
            sort_order=data.sort_order,
            description=data.description or data.item_type.replace("_", " ").title(),
            material_id=data.material_id,
            slab_id=data.slab_id,
            quantity=qty,
            unit=unit,
            unit_sale_price=sale_price,
            unit_cost_price=cost_price,
            line_total_sale=qty * sale_price,
            line_total_cost=qty * cost_price,
            notes=data.notes,
        )
        self.items.add(item)
        _sync(self.db, section)

        record_audit(self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
                     action="item.created", entity_type="quote_item", entity_id=item.id,
                     diff={"item_type": item.item_type, "description": item.description})
        self.db.flush()
        return item


class UpdateItemUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.sections = SectionRepository(db)
        self.items = ItemRepository(db)

    def execute(self, data: UpdateItemInput) -> QuoteSectionItem:
        item = self.items.get(company_id=data.company_id, item_id=data.item_id)
        if item is None:
            raise NotFoundError("Item not found")

        if data.description is not None:
            item.description = data.description
        if data.material_id is not None:
            item.material_id = data.material_id
        if data.slab_id is not None:
            item.slab_id = data.slab_id
        if data.quantity is not None:
            item.quantity = data.quantity
        if data.unit is not None:
            item.unit = data.unit
        if data.unit_sale_price is not None:
            item.unit_sale_price = data.unit_sale_price
        if data.unit_cost_price is not None:
            item.unit_cost_price = data.unit_cost_price
        if data.notes is not None:
            item.notes = data.notes
        if data.sort_order is not None:
            item.sort_order = data.sort_order

        # Recompute line totals.
        item.line_total_sale = Decimal(str(item.quantity)) * Decimal(str(item.unit_sale_price))
        item.line_total_cost = Decimal(str(item.quantity)) * Decimal(str(item.unit_cost_price))

        section = self.sections.get(company_id=item.company_id, section_id=item.section_id)
        if section:
            _sync(self.db, section)
        self.db.flush()
        return item


class DeleteItemUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.sections = SectionRepository(db)
        self.items = ItemRepository(db)

    def execute(self, *, company_id, actor_user_id, item_id) -> None:
        item = self.items.get(company_id=company_id, item_id=item_id)
        if item is None:
            raise NotFoundError("Item not found")
        section = self.sections.get(company_id=company_id, section_id=item.section_id)
        self.items.delete(item)
        if section:
            _sync(self.db, section)
        self.db.flush()
