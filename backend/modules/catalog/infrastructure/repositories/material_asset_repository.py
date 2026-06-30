"""Repositories for the two Material 'asset' join tables -- images and
documents. Grouped in one file since they're structurally identical thin
wrappers around the core Document entity."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.material_document import MaterialDocument
from modules.catalog.infrastructure.models.material_image import MaterialImage


class MaterialImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, image: MaterialImage) -> MaterialImage:
        self.db.add(image)
        self.db.flush()
        return image

    def get(self, *, company_id: uuid.UUID, image_id: uuid.UUID) -> Optional[MaterialImage]:
        return self.db.scalar(
            select(MaterialImage).where(MaterialImage.id == image_id, MaterialImage.company_id == company_id)
        )

    def list_for_material(self, *, company_id: uuid.UUID, material_id: uuid.UUID) -> List[MaterialImage]:
        stmt = (
            select(MaterialImage)
            .where(MaterialImage.company_id == company_id, MaterialImage.material_id == material_id)
            .order_by(MaterialImage.sort_order.asc(), MaterialImage.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, image: MaterialImage) -> None:
        self.db.delete(image)


class MaterialDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, document: MaterialDocument) -> MaterialDocument:
        self.db.add(document)
        self.db.flush()
        return document

    def get(self, *, company_id: uuid.UUID, material_document_id: uuid.UUID) -> Optional[MaterialDocument]:
        return self.db.scalar(
            select(MaterialDocument).where(
                MaterialDocument.id == material_document_id, MaterialDocument.company_id == company_id
            )
        )

    def list_for_material(self, *, company_id: uuid.UUID, material_id: uuid.UUID) -> List[MaterialDocument]:
        stmt = select(MaterialDocument).where(
            MaterialDocument.company_id == company_id, MaterialDocument.material_id == material_id
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, document: MaterialDocument) -> None:
        self.db.delete(document)
