import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.brand import Brand


class BrandRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, brand: Brand) -> Brand:
        self.db.add(brand)
        self.db.flush()
        return brand

    def get(self, *, company_id: uuid.UUID, brand_id: uuid.UUID) -> Optional[Brand]:
        return self.db.scalar(select(Brand).where(Brand.id == brand_id, Brand.company_id == company_id))

    def list(
        self,
        *,
        company_id: uuid.UUID,
        include_hidden: bool = False,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Brand]:
        stmt = select(Brand).where(Brand.company_id == company_id)
        if not include_hidden:
            stmt = stmt.where(Brand.status == "active")
        if search:
            stmt = stmt.where(Brand.name.ilike(f"%{search.strip()}%"))
        stmt = stmt.order_by(Brand.name.asc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
