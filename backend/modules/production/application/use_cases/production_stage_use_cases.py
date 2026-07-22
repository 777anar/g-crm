"""Configurable production stage use cases (Phase 1: Stone Fabrication
Workflow). Stages are per-company, freely renamable/reorderable/hideable
rows -- not a hardcoded enum -- seeded with 8 stone-fabrication defaults
the first time a company's list is requested empty."""
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.production.application.dtos import CreateProductionStageInput, UpdateProductionStageInput
from modules.production.domain import events as production_events
from modules.production.infrastructure.models.production_stage import ProductionStage
from modules.production.infrastructure.repositories.production_stage_repository import ProductionStageRepository

MODULE = "production"


class CreateProductionStageUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.stages = ProductionStageRepository(db)

    def execute(self, data: CreateProductionStageInput) -> ProductionStage:
        existing = self.stages.list(company_id=data.company_id)
        sort_order = data.sort_order if data.sort_order is not None else len(existing)

        stage = ProductionStage(
            company_id=data.company_id,
            name=data.name,
            sort_order=sort_order,
            is_active=True,
        )
        self.stages.add(stage)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="production_stage.created",
            entity_type="production_stage",
            entity_id=stage.id,
            diff={"name": stage.name, "sort_order": stage.sort_order},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=production_events.PRODUCTION_STAGE_CREATED,
                company_id=data.company_id,
                payload={"stage_id": str(stage.id), "name": stage.name},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return stage


class UpdateProductionStageUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.stages = ProductionStageRepository(db)

    def execute(self, data: UpdateProductionStageInput) -> ProductionStage:
        stage = self.stages.get(company_id=data.company_id, stage_id=data.stage_id)
        if stage is None:
            raise NotFoundError("Production stage not found")

        if data.name is not None:
            stage.name = data.name
        if data.sort_order is not None:
            stage.sort_order = data.sort_order
        if data.is_active is not None:
            stage.is_active = data.is_active

        self.db.flush()

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="production_stage.updated",
            entity_type="production_stage",
            entity_id=stage.id,
            diff={},
        )
        return stage
