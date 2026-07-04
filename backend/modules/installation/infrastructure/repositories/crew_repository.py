import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.auth.models import User
from modules.installation.infrastructure.models.crew import Crew
from modules.installation.infrastructure.models.crew_member import CrewMember


class CrewRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, crew: Crew) -> Crew:
        self.db.add(crew)
        self.db.flush()
        return crew

    def get(self, *, company_id: uuid.UUID, crew_id: uuid.UUID) -> Optional[Crew]:
        return self.db.scalar(select(Crew).where(Crew.id == crew_id, Crew.company_id == company_id))

    def list(self, *, company_id: uuid.UUID, status: Optional[str] = None) -> List[Crew]:
        stmt = select(Crew).where(Crew.company_id == company_id)
        if status:
            stmt = stmt.where(Crew.status == status)
        stmt = stmt.order_by(Crew.name.asc())
        return list(self.db.scalars(stmt).all())


class CrewMemberRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, member: CrewMember) -> CrewMember:
        self.db.add(member)
        self.db.flush()
        return member

    def get(self, *, company_id: uuid.UUID, member_id: uuid.UUID) -> Optional[CrewMember]:
        return self.db.scalar(
            select(CrewMember).where(CrewMember.id == member_id, CrewMember.company_id == company_id)
        )

    def get_for_crew_and_user(self, *, company_id: uuid.UUID, crew_id: uuid.UUID, user_id: uuid.UUID) -> Optional[CrewMember]:
        return self.db.scalar(
            select(CrewMember).where(
                CrewMember.company_id == company_id,
                CrewMember.crew_id == crew_id,
                CrewMember.user_id == user_id,
            )
        )

    def list_for_crew(self, *, company_id: uuid.UUID, crew_id: uuid.UUID) -> List[CrewMember]:
        stmt = select(CrewMember).where(CrewMember.company_id == company_id, CrewMember.crew_id == crew_id)
        return list(self.db.scalars(stmt).all())

    def list_with_users_for_crew(self, *, company_id: uuid.UUID, crew_id: uuid.UUID) -> List[tuple[CrewMember, User]]:
        stmt = (
            select(CrewMember, User)
            .join(User, User.id == CrewMember.user_id)
            .where(CrewMember.company_id == company_id, CrewMember.crew_id == crew_id)
        )
        return list(self.db.execute(stmt).all())

    def delete(self, member: CrewMember) -> None:
        self.db.delete(member)
        self.db.flush()
