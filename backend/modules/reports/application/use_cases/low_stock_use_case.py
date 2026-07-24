"""Automated low-stock -> purchase suggestion (Phase 20: Advanced Cut
Optimization & Supply Chain Intelligence). A live snapshot, not
date-ranged -- like Inventory Analytics and Production Planning, current
stock levels aren't meaningful bucketed by a report period."""
import uuid

from sqlalchemy.orm import Session

from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


class LowStockPurchaseSuggestionsUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(
        self, *, company_id: uuid.UUID, stock_threshold: int, no_fit_window_days: int, no_fit_threshold: int
    ) -> dict:
        materials = self.repo.low_stock_materials(
            company_id=company_id,
            stock_threshold=stock_threshold,
            no_fit_window_days=no_fit_window_days,
            no_fit_threshold=no_fit_threshold,
        )
        return {
            "stock_threshold": stock_threshold,
            "no_fit_window_days": no_fit_window_days,
            "no_fit_threshold": no_fit_threshold,
            "materials": [m for m in materials if m["suggested"]],
        }
