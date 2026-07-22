import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.production.domain.value_objects import DEFAULT_PRODUCTION_STAGES
from modules.production.infrastructure.models.production_stage import ProductionStage


class ProductionStageRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, stage: ProductionStage) -> ProductionStage:
        self.db.add(stage)
        self.db.flush()
        return stage

    def get(self, *, company_id: uuid.UUID, stage_id: uuid.UUID) -> Optional[ProductionStage]:
        return self.db.scalar(
            select(ProductionStage).where(ProductionStage.id == stage_id, ProductionStage.company_id == company_id)
        )

    def list(self, *, company_id: uuid.UUID, include_hidden: bool = True) -> List[ProductionStage]:
        stmt = select(ProductionStage).where(ProductionStage.company_id == company_id)
        if not include_hidden:
            stmt = stmt.where(ProductionStage.is_active.is_(True))
        stmt = stmt.order_by(ProductionStage.sort_order.asc())
        return list(self.db.scalars(stmt).all())

    def list_or_seed_defaults(self, *, company_id: uuid.UUID) -> List[ProductionStage]:
        """Lazily seeds the 8 stone-fabrication default stages the first
        time a company has none -- so every existing and future company
        gets a working stage pipeline with no migration-time data seeding
        and no company-creation-flow coupling."""
        existing = self.list(company_id=company_id)
        if existing:
            return existing

        seeded = []
        for i, name in enumerate(DEFAULT_PRODUCTION_STAGES):
            stage = ProductionStage(company_id=company_id, name=name, sort_order=i, is_active=True)
            self.db.add(stage)
            seeded.append(stage)
        self.db.flush()
        return seeded
