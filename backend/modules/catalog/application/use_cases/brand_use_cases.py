from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreateBrandInput, UpdateBrandInput
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS
from modules.catalog.infrastructure.models.brand import Brand
from modules.catalog.infrastructure.repositories.brand_repository import BrandRepository

MODULE_NAME = "catalog"


class CreateBrandUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.brands = BrandRepository(db)

    def execute(self, data: CreateBrandInput) -> Brand:
        brand = Brand(
            company_id=data.company_id,
            name=data.name,
            description=data.description,
            logo_document_id=data.logo_document_id,
            status=DEFAULT_ENTITY_STATUS,
            created_by=data.actor_user_id,
        )
        self.brands.add(brand)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="brand.created",
            entity_type="brand",
            entity_id=brand.id,
            diff={"name": brand.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.BRAND_CREATED,
                company_id=data.company_id,
                payload={"brand_id": str(brand.id), "name": brand.name},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return brand


class UpdateBrandUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.brands = BrandRepository(db)

    def execute(self, data: UpdateBrandInput) -> Brand:
        brand = self.brands.get(company_id=data.company_id, brand_id=data.brand_id)
        if brand is None:
            raise NotFoundError("Brand not found")

        diff = {}
        for field_name in ("name", "description", "status"):
            new_value = getattr(data, field_name)
            if new_value is not None and new_value != getattr(brand, field_name):
                diff[field_name] = {"old": getattr(brand, field_name), "new": new_value}
                setattr(brand, field_name, new_value)
        if data.logo_document_id is not None and data.logo_document_id != brand.logo_document_id:
            diff["logo_document_id"] = {"old": str(brand.logo_document_id), "new": str(data.logo_document_id)}
            brand.logo_document_id = data.logo_document_id

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="brand.updated",
            entity_type="brand",
            entity_id=brand.id,
            diff=diff,
        )
        self.db.flush()
        return brand
