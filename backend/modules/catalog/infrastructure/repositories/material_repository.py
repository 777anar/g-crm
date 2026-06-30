import uuid
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.material import StoneMaterial

_SORTABLE_COLUMNS = {
    "name": StoneMaterial.name,
    "created_at": StoneMaterial.created_at,
    "material_type": StoneMaterial.material_type,
}
DEFAULT_SORT = "name"


class MaterialRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, material: StoneMaterial) -> StoneMaterial:
        self.db.add(material)
        self.db.flush()
        return material

    def get(self, *, company_id: uuid.UUID, material_id: uuid.UUID) -> Optional[StoneMaterial]:
        return self.db.scalar(
            select(StoneMaterial).where(StoneMaterial.id == material_id, StoneMaterial.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        brand_id: Optional[uuid.UUID] = None,
        collection_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[StoneMaterial]:
        stmt = select(StoneMaterial).where(StoneMaterial.company_id == company_id)
        if brand_id:
            stmt = stmt.where(StoneMaterial.brand_id == brand_id)
        if collection_id:
            stmt = stmt.where(StoneMaterial.collection_id == collection_id)
        if status:
            stmt = stmt.where(StoneMaterial.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    StoneMaterial.name.ilike(pattern),
                    StoneMaterial.color.ilike(pattern),
                    StoneMaterial.material_type.ilike(pattern),
                    StoneMaterial.country_of_origin.ilike(pattern),
                )
            )

        sort = sort or DEFAULT_SORT
        descending = sort.startswith("-")
        column = _SORTABLE_COLUMNS.get(sort.lstrip("-"), StoneMaterial.name)
        stmt = stmt.order_by(column.desc() if descending else column.asc())

        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
