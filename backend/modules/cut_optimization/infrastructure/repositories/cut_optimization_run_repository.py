import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.cut_optimization.infrastructure.models.cut_optimization_run import CutOptimizationRun


class CutOptimizationRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, run: CutOptimizationRun) -> CutOptimizationRun:
        self.db.add(run)
        self.db.flush()
        return run

    def get(self, *, company_id: uuid.UUID, run_id: uuid.UUID) -> Optional[CutOptimizationRun]:
        return self.db.scalar(
            select(CutOptimizationRun).where(
                CutOptimizationRun.id == run_id, CutOptimizationRun.company_id == company_id
            )
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        material_id: Optional[uuid.UUID] = None,
        slab_id: Optional[uuid.UUID] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[CutOptimizationRun]:
        stmt = select(CutOptimizationRun).where(CutOptimizationRun.company_id == company_id)
        if material_id:
            stmt = stmt.where(CutOptimizationRun.material_id == material_id)
        if slab_id:
            stmt = stmt.where(CutOptimizationRun.slab_id == slab_id)
        stmt = stmt.order_by(CutOptimizationRun.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
