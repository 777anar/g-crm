import uuid

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.sales.application.dtos import CreateRoomInput, UpdateRoomInput
from modules.sales.domain import events as sales_events
from modules.sales.infrastructure.models.room import Room
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository
from modules.sales.infrastructure.repositories.project_repository import ProjectRepository
from modules.sales.infrastructure.repositories.room_repository import RoomRepository

MODULE = "sales"


class CreateRoomUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.rooms = RoomRepository(db)

    def execute(self, data: CreateRoomInput) -> Room:
        if self.projects.get(company_id=data.company_id, project_id=data.project_id) is None:
            raise NotFoundError("Project not found")

        room = Room(
            company_id=data.company_id,
            project_id=data.project_id,
            room_type=data.room_type,
            name=data.name,
            notes=data.notes,
            sort_order=data.sort_order,
        )
        self.rooms.add(room)

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="room.created", entity_type="room", entity_id=room.id,
            diff={"room_type": room.room_type, "project_id": str(room.project_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.ROOM_CREATED,
                company_id=data.company_id,
                payload={"room_id": str(room.id), "project_id": str(room.project_id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return room


class UpdateRoomUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.rooms = RoomRepository(db)

    def execute(self, data: UpdateRoomInput) -> Room:
        room = self.rooms.get(company_id=data.company_id, room_id=data.room_id)
        if room is None:
            raise NotFoundError("Room not found")

        if data.room_type is not None:
            room.room_type = data.room_type
        if data.name is not None:
            room.name = data.name
        if data.notes is not None:
            room.notes = data.notes
        if data.sort_order is not None:
            room.sort_order = data.sort_order

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="room.updated", entity_type="room", entity_id=room.id, diff={},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.ROOM_UPDATED,
                company_id=data.company_id,
                payload={"room_id": str(room.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return room


class DeleteRoomUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.rooms = RoomRepository(db)
        self.items = ProjectItemRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, room_id: uuid.UUID) -> None:
        room = self.rooms.get(company_id=company_id, room_id=room_id)
        if room is None:
            raise NotFoundError("Room not found")

        for item in self.items.list_for_room(company_id=company_id, room_id=room_id):
            self.items.delete(item)

        self.rooms.delete(room)

        record_audit(
            self.db, company_id=company_id, module=MODULE, actor_user_id=actor_user_id,
            action="room.deleted", entity_type="room", entity_id=room_id, diff={},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.ROOM_DELETED,
                company_id=company_id,
                payload={"room_id": str(room_id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
