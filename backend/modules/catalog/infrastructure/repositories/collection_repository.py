import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.collection import Collection


class CollectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, collection: Collection) -> Collection:
        self.db.add(collection)
        self.db.flush()
        return collection

    def get(self, *, company_id: uuid.UUID, collection_id: uuid.UUID) -> Optional[Collection]:
        return self.db.scalar(
            select(Collection).where(Collection.id == collection_id, Collection.company_id == company_id)
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        brand_id: Optional[uuid.UUID] = None,
        include_hidden: bool = False,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Collection]:
        stmt = select(Collection).where(Collection.company_id == company_id)
        if brand_id:
            stmt = stmt.where(Collection.brand_id == brand_id)
        if not include_hidden:
            stmt = stmt.where(Collection.status == "active")
        if search:
            stmt = stmt.where(Collection.name.ilike(f"%{search.strip()}%"))
        stmt = stmt.order_by(Collection.name.asc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
