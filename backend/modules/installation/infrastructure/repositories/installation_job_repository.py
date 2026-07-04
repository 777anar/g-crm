import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.installation.infrastructure.models.installation_job import InstallationJob
from modules.installation.infrastructure.models.installation_job_number_sequence import (
    InstallationJobNumberSequence,
)


class InstallationJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, job: InstallationJob) -> InstallationJob:
        self.db.add(job)
        self.db.flush()
        return job

    def get(self, *, company_id: uuid.UUID, job_id: uuid.UUID) -> Optional[InstallationJob]:
        return self.db.scalar(
            select(InstallationJob).where(InstallationJob.id == job_id, InstallationJob.company_id == company_id)
        )

    def get_for_order(self, *, company_id: uuid.UUID, order_id: uuid.UUID) -> Optional[InstallationJob]:
        return self.db.scalar(
            select(InstallationJob).where(
                InstallationJob.order_id == order_id, InstallationJob.company_id == company_id
            )
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        status: Optional[str] = None,
        crew_id: Optional[uuid.UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[InstallationJob]:
        stmt = select(InstallationJob).where(InstallationJob.company_id == company_id)
        if status:
            stmt = stmt.where(InstallationJob.status == status)
        if crew_id:
            stmt = stmt.where(InstallationJob.crew_id == crew_id)
        if date_from:
            stmt = stmt.where(InstallationJob.scheduled_date >= date_from)
        if date_to:
            stmt = stmt.where(InstallationJob.scheduled_date <= date_to)
        if search:
            stmt = stmt.where(InstallationJob.job_number.ilike(f"%{search}%"))
        stmt = stmt.order_by(InstallationJob.scheduled_date.asc().nulls_last(), InstallationJob.route_sequence.asc())
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_for_crew_on_date(self, *, company_id: uuid.UUID, crew_id: uuid.UUID, date: str) -> List[InstallationJob]:
        stmt = (
            select(InstallationJob)
            .where(
                InstallationJob.company_id == company_id,
                InstallationJob.crew_id == crew_id,
                InstallationJob.scheduled_date == date,
            )
            .order_by(InstallationJob.route_sequence.asc().nulls_last())
        )
        return list(self.db.scalars(stmt).all())

    def next_job_number(self, *, company_id: uuid.UUID, year: int) -> str:
        """Atomically increments the per-company-per-year counter and returns
        a formatted job number like 'INST-2026-0001'."""
        seq = self.db.scalar(
            select(InstallationJobNumberSequence).where(
                InstallationJobNumberSequence.company_id == company_id,
                InstallationJobNumberSequence.year == year,
            )
        )
        if seq is None:
            seq = InstallationJobNumberSequence(company_id=company_id, year=year, last_number=0)
            self.db.add(seq)
            self.db.flush()
        seq.last_number += 1
        self.db.flush()
        return f"INST-{year}-{seq.last_number:04d}"
