import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.room import Room


class RoomRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, room: Room) -> Room:
        self.db.add(room)
        self.db.flush()
        return room

    def get(self, *, company_id: uuid.UUID, room_id: uuid.UUID) -> Optional[Room]:
        return self.db.scalar(
            select(Room).where(Room.id == room_id, Room.company_id == company_id)
        )

    def list_for_project(self, *, company_id: uuid.UUID, project_id: uuid.UUID) -> List[Room]:
        stmt = (
            select(Room)
            .where(Room.company_id == company_id, Room.project_id == project_id)
            .order_by(Room.sort_order.asc(), Room.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, room: Room) -> None:
        self.db.delete(room)
        self.db.flush()
