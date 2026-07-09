import uuid

from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from modules.catalog.application.dtos import AddMaterialSizeInput, AddMaterialThicknessInput
from modules.catalog.infrastructure.models.material_size import MaterialSize
from modules.catalog.infrastructure.models.material_thickness import MaterialThickness
from modules.catalog.infrastructure.repositories.material_option_repository import (
    MaterialSizeRepository,
    MaterialThicknessRepository,
)
from modules.catalog.infrastructure.repositories.material_repository import MaterialRepository

MODULE_NAME = "catalog"


class AddMaterialThicknessUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.materials = MaterialRepository(db)
        self.thicknesses = MaterialThicknessRepository(db)

    def execute(self, data: AddMaterialThicknessInput) -> MaterialThickness:
        if self.materials.get(company_id=data.company_id, material_id=data.material_id) is None:
            raise NotFoundError("Material not found")

        thickness = MaterialThickness(
            company_id=data.company_id,
            material_id=data.material_id,
            thickness_mm=data.thickness_mm,
            sort_order=data.sort_order,
        )
        self.thicknesses.add(thickness)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="material.thickness_added",
            entity_type="material",
            entity_id=data.material_id,
            diff={"thickness_id": str(thickness.id), "thickness_mm": thickness.thickness_mm},
        )
        self.db.flush()
        return thickness


class DeleteMaterialThicknessUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.thicknesses = MaterialThicknessRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, thickness_id: uuid.UUID) -> None:
        thickness = self.thicknesses.get(company_id=company_id, thickness_id=thickness_id)
        if thickness is None:
            raise NotFoundError("Thickness option not found")
        material_id = thickness.material_id
        self.thicknesses.delete(thickness)

        record_audit(
            self.db,
            company_id=company_id,
            module=MODULE_NAME,
            actor_user_id=actor_user_id,
            action="material.thickness_removed",
            entity_type="material",
            entity_id=material_id,
            diff={"thickness_id": str(thickness_id)},
        )
        self.db.flush()


class AddMaterialSizeUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.materials = MaterialRepository(db)
        self.sizes = MaterialSizeRepository(db)

    def execute(self, data: AddMaterialSizeInput) -> MaterialSize:
        if self.materials.get(company_id=data.company_id, material_id=data.material_id) is None:
            raise NotFoundError("Material not found")

        size = MaterialSize(
            company_id=data.company_id,
            material_id=data.material_id,
            dimensions=data.dimensions,
            sort_order=data.sort_order,
        )
        self.sizes.add(size)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="material.size_added",
            entity_type="material",
            entity_id=data.material_id,
            diff={"size_id": str(size.id), "dimensions": size.dimensions},
        )
        self.db.flush()
        return size


class DeleteMaterialSizeUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.sizes = MaterialSizeRepository(db)

    def execute(self, *, company_id: uuid.UUID, actor_user_id: uuid.UUID, size_id: uuid.UUID) -> None:
        size = self.sizes.get(company_id=company_id, size_id=size_id)
        if size is None:
            raise NotFoundError("Size option not found")
        material_id = size.material_id
        self.sizes.delete(size)

        record_audit(
            self.db,
            company_id=company_id,
            module=MODULE_NAME,
            actor_user_id=actor_user_id,
            action="material.size_removed",
            entity_type="material",
            entity_id=material_id,
            diff={"size_id": str(size_id)},
        )
        self.db.flush()
