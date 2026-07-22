import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.domain.value_objects import SLAB_STATUS_AVAILABLE
from modules.catalog.infrastructure.models.material import StoneMaterial
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

    def search_offcuts(
        self,
        *,
        company_id: uuid.UUID,
        material_id: Optional[uuid.UUID] = None,
        thickness_mm: Optional[str] = None,
        finish: Optional[str] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        min_length_mm: Optional[Decimal] = None,
        min_width_mm: Optional[Decimal] = None,
        min_area_m2: Optional[Decimal] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Slab]:
        """The Offcut Library search surface (Phase 2 requirement #3):
        every `available` offcut slab, filterable by material/thickness/
        finish (joined from Material, since those live there, not on the
        Slab row itself) and by minimum usable dimensions/area -- "does
        this remnant have enough room for what I need" is the whole point
        of browsing offcuts rather than reserving a fresh slab."""
        stmt = (
            select(Slab)
            .join(StoneMaterial, StoneMaterial.id == Slab.material_id)
            .where(
                Slab.company_id == company_id,
                Slab.is_offcut.is_(True),
                Slab.status == SLAB_STATUS_AVAILABLE,
            )
        )
        if material_id:
            stmt = stmt.where(Slab.material_id == material_id)
        if warehouse_id:
            stmt = stmt.where(Slab.warehouse_id == warehouse_id)
        if thickness_mm:
            stmt = stmt.where(StoneMaterial.thickness_mm == thickness_mm)
        if finish:
            stmt = stmt.where(StoneMaterial.finish == finish)
        if min_length_mm is not None:
            stmt = stmt.where(Slab.length_mm >= min_length_mm)
        if min_width_mm is not None:
            stmt = stmt.where(Slab.width_mm >= min_width_mm)
        if min_area_m2 is not None:
            stmt = stmt.where(Slab.area_m2 >= min_area_m2)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(Slab.slab_number.ilike(pattern))

        stmt = stmt.order_by(Slab.area_m2.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_offcut_candidates(
        self,
        *,
        company_id: uuid.UUID,
        material_id: uuid.UUID,
        thickness_mm: Optional[str] = None,
        finish: Optional[str] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> List[Slab]:
        """Every candidate for Smart Offcut recommendation (requirement
        #2) -- same filters as `search_offcuts` minus the dimension/area
        gates, since those are evaluated by actually running the nesting
        algorithm against each candidate rather than a blunt >= filter."""
        return self.search_offcuts(
            company_id=company_id, material_id=material_id, thickness_mm=thickness_mm,
            finish=finish, warehouse_id=warehouse_id, limit=1000, offset=0,
        )
