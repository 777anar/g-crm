"""Repositories for the two Material 'option' tables -- thicknesses and
sizes. Grouped in one file since they're structurally identical thin
wrappers, mirroring material_asset_repository.py's images/documents pair."""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.material_size import MaterialSize
from modules.catalog.infrastructure.models.material_thickness import MaterialThickness


class MaterialThicknessRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, thickness: MaterialThickness) -> MaterialThickness:
        self.db.add(thickness)
        self.db.flush()
        return thickness

    def get(self, *, company_id: uuid.UUID, thickness_id: uuid.UUID) -> Optional[MaterialThickness]:
        return self.db.scalar(
            select(MaterialThickness).where(
                MaterialThickness.id == thickness_id, MaterialThickness.company_id == company_id
            )
        )

    def list_for_material(self, *, company_id: uuid.UUID, material_id: uuid.UUID) -> List[MaterialThickness]:
        stmt = (
            select(MaterialThickness)
            .where(MaterialThickness.company_id == company_id, MaterialThickness.material_id == material_id)
            .order_by(MaterialThickness.sort_order.asc(), MaterialThickness.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, thickness: MaterialThickness) -> None:
        self.db.delete(thickness)


class MaterialSizeRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, size: MaterialSize) -> MaterialSize:
        self.db.add(size)
        self.db.flush()
        return size

    def get(self, *, company_id: uuid.UUID, size_id: uuid.UUID) -> Optional[MaterialSize]:
        return self.db.scalar(
            select(MaterialSize).where(MaterialSize.id == size_id, MaterialSize.company_id == company_id)
        )

    def list_for_material(self, *, company_id: uuid.UUID, material_id: uuid.UUID) -> List[MaterialSize]:
        stmt = (
            select(MaterialSize)
            .where(MaterialSize.company_id == company_id, MaterialSize.material_id == material_id)
            .order_by(MaterialSize.sort_order.asc(), MaterialSize.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, size: MaterialSize) -> None:
        self.db.delete(size)
