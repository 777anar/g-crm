from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.catalog.application.dtos import CreateCollectionInput, UpdateCollectionInput
from modules.catalog.domain import events as catalog_events
from modules.catalog.domain.value_objects import DEFAULT_ENTITY_STATUS
from modules.catalog.infrastructure.models.collection import Collection
from modules.catalog.infrastructure.repositories.brand_repository import BrandRepository
from modules.catalog.infrastructure.repositories.collection_repository import CollectionRepository

MODULE_NAME = "catalog"


class CreateCollectionUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.collections = CollectionRepository(db)
        self.brands = BrandRepository(db)

    def execute(self, data: CreateCollectionInput) -> Collection:
        if self.brands.get(company_id=data.company_id, brand_id=data.brand_id) is None:
            raise NotFoundError("Brand not found")

        collection = Collection(
            company_id=data.company_id,
            brand_id=data.brand_id,
            name=data.name,
            description=data.description,
            status=DEFAULT_ENTITY_STATUS,
            created_by=data.actor_user_id,
        )
        self.collections.add(collection)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="collection.created",
            entity_type="collection",
            entity_id=collection.id,
            diff={"name": collection.name, "brand_id": str(collection.brand_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=catalog_events.COLLECTION_CREATED,
                company_id=data.company_id,
                payload={"collection_id": str(collection.id), "brand_id": str(collection.brand_id)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return collection


class UpdateCollectionUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.collections = CollectionRepository(db)

    def execute(self, data: UpdateCollectionInput) -> Collection:
        collection = self.collections.get(company_id=data.company_id, collection_id=data.collection_id)
        if collection is None:
            raise NotFoundError("Collection not found")

        diff = {}
        for field_name in ("name", "description", "status"):
            new_value = getattr(data, field_name)
            if new_value is not None and new_value != getattr(collection, field_name):
                diff[field_name] = {"old": getattr(collection, field_name), "new": new_value}
                setattr(collection, field_name, new_value)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="collection.updated",
            entity_type="collection",
            entity_id=collection.id,
            diff=diff,
        )
        self.db.flush()
        return collection
