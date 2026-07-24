import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.cut_optimization.infrastructure.models.cut_optimization_batch_run import CutOptimizationBatchRun


class CutOptimizationBatchRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, run: CutOptimizationBatchRun) -> CutOptimizationBatchRun:
        self.db.add(run)
        self.db.flush()
        return run

    def get(self, *, company_id: uuid.UUID, run_id: uuid.UUID) -> Optional[CutOptimizationBatchRun]:
        return self.db.scalar(
            select(CutOptimizationBatchRun).where(
                CutOptimizationBatchRun.id == run_id, CutOptimizationBatchRun.company_id == company_id
            )
        )

    def list(
        self,
        *,
        company_id: uuid.UUID,
        material_id: Optional[uuid.UUID] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[CutOptimizationBatchRun]:
        stmt = select(CutOptimizationBatchRun).where(CutOptimizationBatchRun.company_id == company_id)
        if material_id:
            stmt = stmt.where(CutOptimizationBatchRun.material_id == material_id)
        stmt = stmt.order_by(CutOptimizationBatchRun.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
