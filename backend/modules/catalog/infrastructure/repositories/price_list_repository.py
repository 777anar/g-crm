import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.catalog.infrastructure.models.price_list import PriceList, PriceListEntry


class PriceListRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, price_list: PriceList) -> PriceList:
        self.db.add(price_list)
        self.db.flush()
        return price_list

    def get(self, *, company_id: uuid.UUID, price_list_id: uuid.UUID) -> Optional[PriceList]:
        return self.db.scalar(
            select(PriceList).where(PriceList.id == price_list_id, PriceList.company_id == company_id)
        )

    def list(self, *, company_id: uuid.UUID, include_hidden: bool = False) -> List[PriceList]:
        stmt = select(PriceList).where(PriceList.company_id == company_id)
        if not include_hidden:
            stmt = stmt.where(PriceList.status == "active")
        stmt = stmt.order_by(PriceList.name.asc())
        return list(self.db.scalars(stmt).all())


class PriceListEntryRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, entry: PriceListEntry) -> PriceListEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def get(self, *, company_id: uuid.UUID, entry_id: uuid.UUID) -> Optional[PriceListEntry]:
        return self.db.scalar(
            select(PriceListEntry).where(
                PriceListEntry.id == entry_id, PriceListEntry.company_id == company_id
            )
        )

    def get_for_material(
        self, *, company_id: uuid.UUID, price_list_id: uuid.UUID, material_id: uuid.UUID
    ) -> Optional[PriceListEntry]:
        return self.db.scalar(
            select(PriceListEntry).where(
                PriceListEntry.company_id == company_id,
                PriceListEntry.price_list_id == price_list_id,
                PriceListEntry.material_id == material_id,
            )
        )

    def list_for_price_list(self, *, company_id: uuid.UUID, price_list_id: uuid.UUID) -> List[PriceListEntry]:
        stmt = select(PriceListEntry).where(
            PriceListEntry.company_id == company_id, PriceListEntry.price_list_id == price_list_id
        )
        return list(self.db.scalars(stmt).all())

    def list_for_material(self, *, company_id: uuid.UUID, material_id: uuid.UUID) -> List[PriceListEntry]:
        stmt = select(PriceListEntry).where(
            PriceListEntry.company_id == company_id, PriceListEntry.material_id == material_id
        )
        return list(self.db.scalars(stmt).all())
