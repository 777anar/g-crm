from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreateMaterialInput, UpdateMaterialInput
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.value_objects import DEFAULT_MATERIAL_STATUS
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.catalog.infrastructure.repositories.brand_repository import BrandRepository
from modules.catalog.infrastructure.repositories.collection_repository import CollectionRepository
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository

MODULE_NAME = "catalog"

_UPDATABLE_FIELDS = (
    "name",
    "material_type",
    "color",
    "finish",
    "thickness_mm",
    "dimensions",
    "country_of_origin",
    "description",
    "status",
)


def _validate_collection_belongs_to_brand(db: Session, *, company_id, brand_id, collection_id) -> None:
    if collection_id is None:
        return
    collection = CollectionRepository(db).get(company_id=company_id, collection_id=collection_id)
    if collection is None:
        raise ValidationAPIError(
            "collection_id does not refer to a collection in this company",
            details=[{"field": "collection_id", "issue": "not found"}],
        )
    if str(collection.brand_id) != str(brand_id):
        raise ValidationAPIError(
            "collection does not belong to the given brand",
            details=[{"field": "collection_id", "issue": "brand mismatch"}],
        )


class CreateMaterialUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.materials = MaterialRepository(db)
        self.brands = BrandRepository(db)

    def execute(self, data: CreateMaterialInput) -> StoneMaterial:
        if self.brands.get(company_id=data.company_id, brand_id=data.brand_id) is None:
            raise NotFoundError("Brand not found")
        _validate_collection_belongs_to_brand(
            self.db, company_id=data.company_id, brand_id=data.brand_id, collection_id=data.collection_id
        )

        material = StoneMaterial(
            company_id=data.company_id,
            brand_id=data.brand_id,
            collection_id=data.collection_id,
            name=data.name,
            material_type=data.material_type,
            color=data.color,
            finish=data.finish,
            thickness_mm=data.thickness_mm,
            dimensions=data.dimensions,
            country_of_origin=data.country_of_origin,
            description=data.description,
            status=data.status or DEFAULT_MATERIAL_STATUS,
            created_by=data.actor_user_id,
        )
        self.materials.add(material)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="material.created",
            entity_type="material",
            entity_id=material.id,
            diff={"name": material.name, "brand_id": str(material.brand_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.MATERIAL_CREATED,
                company_id=data.company_id,
                payload={"material_id": str(material.id), "name": material.name, "brand_id": str(material.brand_id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return material


class UpdateMaterialUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.materials = MaterialRepository(db)
        self.brands = BrandRepository(db)

    def execute(self, data: UpdateMaterialInput) -> StoneMaterial:
        material = self.materials.get(company_id=data.company_id, material_id=data.material_id)
        if material is None:
            raise NotFoundError("Material not found")

        target_brand_id = data.brand_id if data.brand_id is not None else material.brand_id
        if data.brand_id is not None and self.brands.get(company_id=data.company_id, brand_id=data.brand_id) is None:
            raise NotFoundError("Brand not found")
        if data.collection_id is not None:
            _validate_collection_belongs_to_brand(
                self.db, company_id=data.company_id, brand_id=target_brand_id, collection_id=data.collection_id
            )

        diff = {}
        if data.brand_id is not None and data.brand_id != material.brand_id:
            diff["brand_id"] = {"old": str(material.brand_id), "new": str(data.brand_id)}
            material.brand_id = data.brand_id
        if data.collection_id is not None and data.collection_id != material.collection_id:
            diff["collection_id"] = {
                "old": str(material.collection_id) if material.collection_id else None,
                "new": str(data.collection_id),
            }
            material.collection_id = data.collection_id
        for field_name in _UPDATABLE_FIELDS:
            new_value = getattr(data, field_name)
            if new_value is not None and new_value != getattr(material, field_name):
                diff[field_name] = {"old": getattr(material, field_name), "new": new_value}
                setattr(material, field_name, new_value)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="material.updated",
            entity_type="material",
            entity_id=material.id,
            diff=diff,
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.MATERIAL_UPDATED,
                company_id=data.company_id,
                payload={"material_id": str(material.id), "diff": diff},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return material
