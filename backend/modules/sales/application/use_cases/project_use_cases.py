from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.sales.application.dtos import CreateProjectInput, UpdateProjectInput
from modules.sales.domain import events as sales_events
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.repositories.project_repository import ProjectRepository

MODULE = "sales"


class CreateProjectUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProjectRepository(db)

    def execute(self, data: CreateProjectInput) -> Project:
        project = Project(
            company_id=data.company_id,
            customer_id=data.customer_id,
            name=data.name,
            project_type=data.project_type,
            address=data.address,
            notes=data.notes,
            assigned_to=data.assigned_to,
        )
        self.repo.add(project)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="project.created",
            entity_type="project",
            entity_id=project.id,
            diff={"name": project.name, "customer_id": str(project.customer_id)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_CREATED,
                company_id=data.company_id,
                payload={"project_id": str(project.id), "customer_id": str(project.customer_id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return project


class UpdateProjectUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProjectRepository(db)

    def execute(self, data: UpdateProjectInput) -> Project:
        project = self.repo.get(company_id=data.company_id, project_id=data.project_id)
        if project is None:
            raise NotFoundError("Project not found")

        diff = {}
        if data.name is not None:
            diff["name"] = {"old": project.name, "new": data.name}
            project.name = data.name
        if data.project_type is not None:
            project.project_type = data.project_type
        if data.address is not None:
            project.address = data.address
        if data.notes is not None:
            project.notes = data.notes
        if data.assigned_to is not None:
            project.assigned_to = data.assigned_to
        if data.status is not None:
            project.status = data.status

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="project.updated",
            entity_type="project",
            entity_id=project.id,
            diff=diff,
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_UPDATED,
                company_id=data.company_id,
                payload={"project_id": str(project.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return project
