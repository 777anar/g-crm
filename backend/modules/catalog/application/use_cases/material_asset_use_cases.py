from sqlalchemy.orm import Session

from core.api.errors import NotFoundError, ValidationAPIError
from core.audit.service import record_audit
from modules.catalog.application.dtos import AddMaterialDocumentInput, AddMaterialImageInput
from modules.catalog.domain.value_objects import VALID_DOCUMENT_TYPES, VALID_IMAGE_TYPES
from modules.catalog.infrastructure.models.material_document import MaterialDocument
from modules.catalog.infrastructure.models.material_image import MaterialImage
from modules.catalog.infrastructure.repositories.material_asset_repository import (
    MaterialDocumentRepository,
    MaterialImageRepository,
)
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository

MODULE_NAME = "catalog"


class AddMaterialImageUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.materials = MaterialRepository(db)
        self.images = MaterialImageRepository(db)

    def execute(self, data: AddMaterialImageInput) -> MaterialImage:
        if self.materials.get(company_id=data.company_id, material_id=data.material_id) is None:
            raise NotFoundError("Material not found")
        if data.image_type not in VALID_IMAGE_TYPES:
            raise ValidationAPIError(
                f"image_type must be one of {sorted(VALID_IMAGE_TYPES)}",
                details=[{"field": "image_type", "issue": "invalid"}],
            )

        image = MaterialImage(
            company_id=data.company_id,
            material_id=data.material_id,
            document_id=data.document_id,
            image_type=data.image_type,
            sort_order=data.sort_order,
        )
        self.images.add(image)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="material.image_added",
            entity_type="material",
            entity_id=data.material_id,
            diff={"image_id": str(image.id), "image_type": image.image_type},
        )
        self.db.flush()
        return image


class AddMaterialDocumentUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.materials = MaterialRepository(db)
        self.documents = MaterialDocumentRepository(db)

    def execute(self, data: AddMaterialDocumentInput) -> MaterialDocument:
        if self.materials.get(company_id=data.company_id, material_id=data.material_id) is None:
            raise NotFoundError("Material not found")
        if data.document_type not in VALID_DOCUMENT_TYPES:
            raise ValidationAPIError(
                f"document_type must be one of {sorted(VALID_DOCUMENT_TYPES)}",
                details=[{"field": "document_type", "issue": "invalid"}],
            )

        material_document = MaterialDocument(
            company_id=data.company_id,
            material_id=data.material_id,
            document_id=data.document_id,
            document_type=data.document_type,
        )
        self.documents.add(material_document)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="material.document_added",
            entity_type="material",
            entity_id=data.material_id,
            diff={"material_document_id": str(material_document.id), "document_type": material_document.document_type},
        )
        self.db.flush()
        return material_document
