import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.sales.application.dtos import CreateProjectItemInput, UpdateProjectItemInput
from modules.sales.domain import events as sales_events
from modules.sales.domain.value_objects import ITEM_TYPE_DEFAULT_UNIT
from modules.sales.infrastructure.models.project_item import ProjectItem
from modules.sales.infrastructure.repositories.project_item_drawing_repository import ProjectItemDrawingRepository
from modules.sales.infrastructure.repositories.project_item_measurement_repository import (
    ProjectItemMeasurementRepository,
)
from modules.sales.infrastructure.repositories.project_item_photo_repository import ProjectItemPhotoRepository
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository
from modules.sales.infrastructure.repositories.room_repository import RoomRepository

MODULE = "sales"


class CreateProjectItemUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.rooms = RoomRepository(db)
        self.items = ProjectItemRepository(db)

    def execute(self, data: CreateProjectItemInput) -> ProjectItem:
        room = self.rooms.get(company_id=data.company_id, room_id=data.room_id)
        if room is None:
            raise NotFoundError("Room not found")

        unit = data.unit or ITEM_TYPE_DEFAULT_UNIT.get(data.item_type, "unit")
        item = ProjectItem(
            company_id=data.company_id,
            project_id=room.project_id,
            room_id=data.room_id,
            item_type=data.item_type,
            name=data.name,
            material_id=data.material_id,
            material_thickness_id=data.material_thickness_id,
            material_size_id=data.material_size_id,
            quantity=Decimal(str(data.quantity)),
            unit=unit,
            notes=data.notes,
            sort_order=data.sort_order,
        )
        self.items.add(item)

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="project_item.created", entity_type="project_item", entity_id=item.id,
            diff={"item_type": item.item_type, "room_id": str(item.room_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_ITEM_CREATED,
                company_id=data.company_id,
                payload={"project_item_id": str(item.id), "room_id": str(item.room_id), "project_id": str(item.project_id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return item


class UpdateProjectItemUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.items = ProjectItemRepository(db)

    def execute(self, data: UpdateProjectItemInput) -> ProjectItem:
        item = self.items.get(company_id=data.company_id, item_id=data.project_item_id)
        if item is None:
            raise NotFoundError("Project item not found")

        if data.item_type is not None:
            item.item_type = data.item_type
        if data.name is not None:
            item.name = data.name
        if data.material_id is not None:
            item.material_id = data.material_id
        if data.material_thickness_id is not None:
            item.material_thickness_id = data.material_thickness_id
        if data.material_size_id is not None:
            item.material_size_id = data.material_size_id
        if data.quantity is not None:
            item.quantity = Decimal(str(data.quantity))
        if data.unit is not None:
            item.unit = data.unit
        if data.notes is not None:
            item.notes = data.notes
        if data.sort_order is not None:
            item.sort_order = data.sort_order
        if data.production_status is not None:
            item.production_status = data.production_status
        if data.installation_status is not None:
            item.installation_status = data.installation_status

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="project_item.updated", entity_type="project_item", entity_id=item.id, diff={},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_ITEM_UPDATED,
                company_id=data.company_id,
                payload={"project_item_id": str(item.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return item


class DeleteProjectItemUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.items = ProjectItemRepository(db)
        self.measurements = ProjectItemMeasurementRepository(db)
        self.drawings = ProjectItemDrawingRepository(db)
        self.photos = ProjectItemPhotoRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, project_item_id: uuid.UUID) -> None:
        item = self.items.get(company_id=company_id, item_id=project_item_id)
        if item is None:
            raise NotFoundError("Project item not found")

        for m in self.measurements.list_for_item(company_id=company_id, project_item_id=project_item_id):
            self.measurements.delete(m)
        for d in self.drawings.list_for_item(company_id=company_id, project_item_id=project_item_id):
            self.drawings.delete(d)
        for p in self.photos.list_for_item(company_id=company_id, project_item_id=project_item_id):
            self.photos.delete(p)

        self.items.delete(item)

        record_audit(
            self.db, company_id=company_id, module=MODULE, actor_user_id=actor_user_id,
            action="project_item.deleted", entity_type="project_item", entity_id=project_item_id, diff={},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_ITEM_DELETED,
                company_id=company_id,
                payload={"project_item_id": str(project_item_id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
