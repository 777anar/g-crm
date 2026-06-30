import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.slab import Slab

_SORTABLE_COLUMNS = {
    "slab_number": Slab.slab_number,
    "created_at": Slab.created_at,
    "area_m2": Slab.area_m2,
    "status": Slab.status,
}
DEFAULT_SORT = "-created_at"


class SlabRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, slab: Slab) -> Slab:
        self.db.add(slab)
        self.db.flush()
        return slab

    def get(self, *, company_id: uuid.UUID, slab_id: uuid.UUID) -> Optional[Slab]:
        return self.db.scalar(select(Slab).where(Slab.id == slab_id, Slab.company_id == company_id))

    def get_by_slab_number(self, *, company_id: uuid.UUID, slab_number: str) -> Optional[Slab]:
        return self.db.scalar(
            select(Slab).where(Slab.company_id == company_id, Slab.slab_number == slab_number)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        material_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Slab]:
        stmt = select(Slab).where(Slab.company_id == company_id)
        if material_id:
            stmt = stmt.where(Slab.material_id == material_id)
        if warehouse_id:
            stmt = stmt.where(Slab.warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(Slab.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                (Slab.slab_number.ilike(pattern))
                | (Slab.lot_number.ilike(pattern))
                | (Slab.barcode.ilike(pattern))
            )

        sort = sort or DEFAULT_SORT
        descending = sort.startswith("-")
        column = _SORTABLE_COLUMNS.get(sort.lstrip("-"), Slab.created_at)
        stmt = stmt.order_by(column.desc() if descending else column.asc())

        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
