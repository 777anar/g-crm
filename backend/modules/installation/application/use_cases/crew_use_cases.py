"""Crew management use cases: create/update a crew, add/remove members."""
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.installation.application.dtos import (
    AddCrewMemberInput,
    CreateCrewInput,
    RemoveCrewMemberInput,
    UpdateCrewInput,
)
from modules.installation.domain import events as installation_events
from modules.installation.domain.value_objects import DEFAULT_CREW_STATUS, VALID_CREW_STATUSES
from modules.installation.infrastructure.models.crew import Crew
from modules.installation.infrastructure.models.crew_member import CrewMember
from modules.installation.infrastructure.repositories.crew_repository import (
    CrewMemberRepository,
    CrewRepository,
)

MODULE = "installation"


class CreateCrewUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.crews = CrewRepository(db)

    def execute(self, data: CreateCrewInput) -> Crew:
        crew = Crew(
            company_id=data.company_id,
            name=data.name,
            status=DEFAULT_CREW_STATUS,
            notes=data.notes,
            created_by=data.actor_user_id,
        )
        self.crews.add(crew)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="crew.created",
            entity_type="crew",
            entity_id=crew.id,
            diff={"name": crew.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=installation_events.CREW_CREATED,
                company_id=data.company_id,
                payload={"crew_id": str(crew.id), "name": crew.name},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return crew


class UpdateCrewUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.crews = CrewRepository(db)

    def execute(self, data: UpdateCrewInput) -> Crew:
        crew = self.crews.get(company_id=data.company_id, crew_id=data.crew_id)
        if crew is None:
            raise NotFoundError("Crew not found")

        if data.name is not None:
            crew.name = data.name
        if data.status is not None:
            if data.status not in VALID_CREW_STATUSES:
                raise ValidationAPIError(f"status must be one of {sorted(VALID_CREW_STATUSES)}")
            crew.status = data.status
        if data.notes is not None:
            crew.notes = data.notes

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="crew.updated",
            entity_type="crew",
            entity_id=crew.id,
            diff={},
        )
        return crew


class AddCrewMemberUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.crews = CrewRepository(db)
        self.members = CrewMemberRepository(db)

    def execute(self, data: AddCrewMemberInput) -> CrewMember:
        crew = self.crews.get(company_id=data.company_id, crew_id=data.crew_id)
        if crew is None:
            raise NotFoundError("Crew not found")

        if self.members.get_for_crew_and_user(
            company_id=data.company_id, crew_id=data.crew_id, user_id=data.user_id
        ):
            raise ValidationAPIError("This user is already a member of this crew")

        member = CrewMember(
            company_id=data.company_id,
            crew_id=data.crew_id,
            user_id=data.user_id,
            is_lead=data.is_lead,
        )
        self.members.add(member)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="crew.member_added",
            entity_type="crew",
            entity_id=crew.id,
            diff={"user_id": str(data.user_id)},
        )
        self.db.flush()
        return member


class RemoveCrewMemberUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.members = CrewMemberRepository(db)

    def execute(self, data: RemoveCrewMemberInput) -> None:
        member = self.members.get(company_id=data.company_id, member_id=data.member_id)
        if member is None or member.crew_id != data.crew_id:
            raise NotFoundError("Crew member not found")

        self.members.delete(member)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="crew.member_removed",
            entity_type="crew",
            entity_id=data.crew_id,
            diff={"user_id": str(member.user_id)},
        )
