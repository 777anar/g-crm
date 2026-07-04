"""Installation Analytics: derived from the Orders module's ready ->
delivered -> installed statuses and its per-item installation_status field --
same rationale as Production Analytics, there is no dedicated Installation
module yet."""
from sqlalchemy.orm import Session

from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


class InstallationAnalyticsUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        dr = data.date_range

        order_status = dict(self.repo.order_status_snapshot(company_id=company_id))
        item_status = self.repo.order_item_status_counts(company_id=company_id, field="installation_status")

        timestamps = self.repo.order_status_change_timestamps(company_id=company_id, date_range=dr)
        installed_count = 0
        cycle_days = []
        for stamps in timestamps.values():
            if "installed" in stamps:
                installed_count += 1
            start = stamps.get("delivered") or stamps.get("ready")
            end = stamps.get("installed")
            if start and end:
                delta_days = (end - start).total_seconds() / 86400
                if delta_days >= 0:
                    cycle_days.append(delta_days)

        avg_cycle_days = round(sum(cycle_days) / len(cycle_days), 1) if cycle_days else None

        return {
            "date_from": dr.date_from,
            "date_to": dr.date_to,
            "kpis": {
                "orders_awaiting_installation": order_status.get("ready", 0) + order_status.get("delivered", 0),
                "orders_installed": installed_count,
                "avg_installation_cycle_days": avg_cycle_days,
            },
            "order_status_breakdown": [{"status": s, "count": c} for s, c in order_status.items()],
            "item_installation_status": [
                {"status": s or "unassigned", "count": c} for s, c in item_status
            ],
        }
