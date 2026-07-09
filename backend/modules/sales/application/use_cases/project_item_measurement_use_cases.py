import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.sales.application.dtos import CreateProjectItemMeasurementInput, UpdateProjectItemMeasurementInput
from modules.sales.domain import events as sales_events
from modules.sales.infrastructure.models.project_item_measurement import ProjectItemMeasurement
from modules.sales.infrastructure.repositories.project_item_measurement_repository import (
    ProjectItemMeasurementRepository,
)
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository

MODULE = "sales"


def _area_m2(length_mm, width_mm, quantity: int):
    if length_mm is None or width_mm is None:
        return None
    return (Decimal(str(length_mm)) / Decimal("1000")) * (Decimal(str(width_mm)) / Decimal("1000")) * quantity


class CreateProjectItemMeasurementUseCase:
    """Every call creates a new revision -- re-measuring a Project Item never
    overwrites a prior visit's numbers."""

    def __init__(self, db: Session):
        self.db = db
        self.items = ProjectItemRepository(db)
        self.measurements = ProjectItemMeasurementRepository(db)

    def execute(self, data: CreateProjectItemMeasurementInput) -> ProjectItemMeasurement:
        item = self.items.get(company_id=data.company_id, item_id=data.project_item_id)
        if item is None:
            raise NotFoundError("Project item not found")

        next_revision = self.measurements.latest_revision_number(
            company_id=data.company_id, project_item_id=data.project_item_id
        ) + 1

        measurement = ProjectItemMeasurement(
            company_id=data.company_id,
            project_item_id=data.project_item_id,
            revision_number=next_revision,
            status=data.status,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            thickness_mm=data.thickness_mm,
            quantity=data.quantity,
            area_m2=_area_m2(data.length_mm, data.width_mm, data.quantity),
            measurer_name=data.measurer_name,
            measured_at=data.measured_at,
            notes=data.notes,
            created_by=data.actor_user_id,
        )
        self.measurements.add(measurement)

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="project_item.measurement_recorded", entity_type="project_item_measurement", entity_id=measurement.id,
            diff={"project_item_id": str(data.project_item_id), "revision_number": next_revision},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_ITEM_MEASUREMENT_RECORDED,
                company_id=data.company_id,
                payload={
                    "measurement_id": str(measurement.id),
                    "project_item_id": str(data.project_item_id),
                    "revision_number": next_revision,
                },
                published_by_module=MODULE,
            ),
            self.db,
        )
        return measurement


class UpdateProjectItemMeasurementUseCase:
    """Edits the same revision row in place -- for fixing a typo on a revision
    that hasn't been superseded yet, e.g. attaching the customer's signature
    once they sign off. Use Create (a new revision) for an actual re-measure."""

    def __init__(self, db: Session):
        self.db = db
        self.measurements = ProjectItemMeasurementRepository(db)

    def execute(self, data: UpdateProjectItemMeasurementInput) -> ProjectItemMeasurement:
        measurement = self.measurements.get(company_id=data.company_id, measurement_id=data.measurement_id)
        if measurement is None:
            raise NotFoundError("Measurement not found")

        if data.length_mm is not None:
            measurement.length_mm = data.length_mm
        if data.width_mm is not None:
            measurement.width_mm = data.width_mm
        if data.thickness_mm is not None:
            measurement.thickness_mm = data.thickness_mm
        if data.quantity is not None:
            measurement.quantity = data.quantity
        if data.measurer_name is not None:
            measurement.measurer_name = data.measurer_name
        if data.measured_at is not None:
            measurement.measured_at = data.measured_at
        if data.notes is not None:
            measurement.notes = data.notes
        if data.status is not None:
            measurement.status = data.status
        if data.customer_signature_document_id is not None:
            measurement.customer_signature_document_id = data.customer_signature_document_id

        measurement.area_m2 = _area_m2(measurement.length_mm, measurement.width_mm, measurement.quantity)

        record_audit(
            self.db, company_id=data.company_id, module=MODULE, actor_user_id=data.actor_user_id,
            action="project_item.measurement_updated", entity_type="project_item_measurement", entity_id=measurement.id,
            diff={},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_ITEM_MEASUREMENT_UPDATED,
                company_id=data.company_id,
                payload={"measurement_id": str(measurement.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return measurement


class DeleteProjectItemMeasurementUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.measurements = ProjectItemMeasurementRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, measurement_id: uuid.UUID) -> None:
        measurement = self.measurements.get(company_id=company_id, measurement_id=measurement_id)
        if measurement is None:
            raise NotFoundError("Measurement not found")
        self.measurements.delete(measurement)

        record_audit(
            self.db, company_id=company_id, module=MODULE, actor_user_id=actor_user_id,
            action="project_item.measurement_deleted", entity_type="project_item_measurement", entity_id=measurement_id,
            diff={},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=sales_events.PROJECT_ITEM_MEASUREMENT_DELETED,
                company_id=company_id,
                payload={"measurement_id": str(measurement_id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
