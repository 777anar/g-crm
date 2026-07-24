import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sales.infrastructure.models.project_item_measurement import ProjectItemMeasurement


class ProjectItemMeasurementRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, measurement: ProjectItemMeasurement) -> ProjectItemMeasurement:
        self.db.add(measurement)
        self.db.flush()
        return measurement

    def get(self, *, company_id: uuid.UUID, measurement_id: uuid.UUID) -> Optional[ProjectItemMeasurement]:
        return self.db.scalar(
            select(ProjectItemMeasurement).where(
                ProjectItemMeasurement.id == measurement_id,
                ProjectItemMeasurement.company_id == company_id,
            )
        )

    def list_for_item(self, *, company_id: uuid.UUID, project_item_id: uuid.UUID) -> List[ProjectItemMeasurement]:
        stmt = (
            select(ProjectItemMeasurement)
            .where(
                ProjectItemMeasurement.company_id == company_id,
                ProjectItemMeasurement.project_item_id == project_item_id,
            )
            .order_by(ProjectItemMeasurement.revision_number.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_company(
        self, *, company_id: uuid.UUID, date_from: Optional[date] = None, date_to: Optional[date] = None
    ) -> List[ProjectItemMeasurement]:
        stmt = select(ProjectItemMeasurement).where(ProjectItemMeasurement.company_id == company_id)
        if date_from is not None:
            stmt = stmt.where(ProjectItemMeasurement.measured_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(ProjectItemMeasurement.measured_at <= date_to)
        stmt = stmt.order_by(ProjectItemMeasurement.measured_at.desc())
        return list(self.db.scalars(stmt).all())

    def latest_revision_number(self, *, company_id: uuid.UUID, project_item_id: uuid.UUID) -> int:
        existing = self.list_for_item(company_id=company_id, project_item_id=project_item_id)
        return max((m.revision_number for m in existing), default=0)

    def delete(self, measurement: ProjectItemMeasurement) -> None:
        self.db.delete(measurement)
        self.db.flush()

    def get_by_signature_provider_request_id(
        self, *, provider: str, provider_request_id: str
    ) -> Optional[ProjectItemMeasurement]:
        # Webhooks are public (no authenticated active-company context), so
        # this is looked up across every company by the provider's own
        # request id alone -- company_id is taken from the resolved row,
        # never trusted from the request, mirroring Communication's
        # identical `get_by_id_any_company` webhook lookup.
        return self.db.scalar(
            select(ProjectItemMeasurement).where(
                ProjectItemMeasurement.signature_provider == provider,
                ProjectItemMeasurement.signature_provider_request_id == provider_request_id,
            )
        )
