from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from modules.installation.application.dtos import AddInstallationPhotoInput
from modules.installation.domain.value_objects import VALID_PHOTO_TYPES
from modules.installation.infrastructure.models.installation_photo import InstallationPhoto
from modules.installation.infrastructure.repositories.installation_job_repository import (
    InstallationJobRepository,
)
from modules.installation.infrastructure.repositories.installation_photo_repository import (
    InstallationPhotoRepository,
)

MODULE = "installation"


class AddInstallationPhotoUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.jobs = InstallationJobRepository(db)
        self.photos = InstallationPhotoRepository(db)

    def execute(self, data: AddInstallationPhotoInput) -> InstallationPhoto:
        job = self.jobs.get(company_id=data.company_id, job_id=data.job_id)
        if job is None:
            raise NotFoundError("Installation job not found")
        if data.photo_type not in VALID_PHOTO_TYPES:
            raise ValidationAPIError(
                f"photo_type must be one of {sorted(VALID_PHOTO_TYPES)}",
                details=[{"field": "photo_type", "issue": "invalid"}],
            )

        photo = InstallationPhoto(
            company_id=data.company_id,
            installation_job_id=job.id,
            document_id=data.document_id,
            photo_type=data.photo_type,
            caption=data.caption,
            sort_order=data.sort_order,
        )
        self.photos.add(photo)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="installation_job.photo_added",
            entity_type="installation_job",
            entity_id=job.id,
            diff={"photo_id": str(photo.id), "photo_type": photo.photo_type},
        )
        self.db.flush()
        return photo
