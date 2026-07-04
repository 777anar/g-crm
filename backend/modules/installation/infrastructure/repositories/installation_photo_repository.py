import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.installation.infrastructure.models.installation_photo import InstallationPhoto


class InstallationPhotoRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, photo: InstallationPhoto) -> InstallationPhoto:
        self.db.add(photo)
        self.db.flush()
        return photo

    def list_for_job(self, *, company_id: uuid.UUID, installation_job_id: uuid.UUID) -> List[InstallationPhoto]:
        stmt = (
            select(InstallationPhoto)
            .where(
                InstallationPhoto.company_id == company_id,
                InstallationPhoto.installation_job_id == installation_job_id,
            )
            .order_by(InstallationPhoto.sort_order.asc())
        )
        return list(self.db.scalars(stmt).all())
