"""Production Analytics: derived entirely from the Orders module's existing
status workflow (waiting -> measuring -> approved_for_production ->
in_production -> ready) and its per-item production_status field -- there is
no dedicated Production module yet, so this reports on what Orders already
tracks rather than inventing data that doesn't exist."""
from sqlalchemy.orm import Session

from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


class ProductionAnalyticsUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        dr = data.date_range

        order_status = dict(self.repo.order_status_snapshot(company_id=company_id))
        item_status = self.repo.order_item_status_counts(company_id=company_id, field="production_status")

        timestamps = self.repo.order_status_change_timestamps(company_id=company_id, date_range=dr)
        entered_production = 0
        cycle_days = []
        for stamps in timestamps.values():
            if "in_production" in stamps:
                entered_production += 1
            if "in_production" in stamps and "ready" in stamps:
                delta_days = (stamps["ready"] - stamps["in_production"]).total_seconds() / 86400
                if delta_days >= 0:
                    cycle_days.append(delta_days)

        avg_cycle_days = round(sum(cycle_days) / len(cycle_days), 1) if cycle_days else None

        return {
            "date_from": dr.date_from,
            "date_to": dr.date_to,
            "kpis": {
                "orders_in_production": order_status.get("in_production", 0),
                "orders_ready": order_status.get("ready", 0),
                "orders_entered_production": entered_production,
                "orders_completed_production": len(cycle_days),
                "avg_production_cycle_days": avg_cycle_days,
            },
            "order_status_breakdown": [{"status": s, "count": c} for s, c in order_status.items()],
            "item_production_status": [
                {"status": s or "unassigned", "count": c} for s, c in item_status
            ],
        }
