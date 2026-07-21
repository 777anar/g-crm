"""Inventory Analytics: reads the Catalog module's Slab/Material/Warehouse
tables directly (the reports module's manifest has always declared a
dependency on "catalog", per `depends_on` in manifest.py -- this is the
first use case that actually reads it). Stock levels are a live snapshot of
current state, not a date-ranged aggregate like Sales/Finance -- a slab
doesn't stop being "available" because it was created outside the report's
date window -- so unlike the other analytics use cases, the date range here
only shapes the response envelope, not the query itself, mirroring how
Production Analytics' order_status_snapshot already ignores the date range
for its own live counts."""
from sqlalchemy.orm import Session

from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


class InventoryAnalyticsUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        dr = data.date_range

        status_counts = dict(self.repo.slab_status_snapshot(company_id=company_id))
        total_slabs = sum(status_counts.values())

        return {
            "date_from": dr.date_from,
            "date_to": dr.date_to,
            "kpis": {
                "total_slabs": total_slabs,
                "available_slabs": status_counts.get("available", 0),
                "reserved_slabs": status_counts.get("reserved", 0),
                "in_production_slabs": status_counts.get("in_production", 0),
                "sold_slabs": status_counts.get("sold", 0),
                "available_area_m2": self.repo.available_slab_area_m2(company_id=company_id),
                "materials_tracked": self.repo.materials_tracked_count(company_id=company_id),
                "materials_out_of_stock": self.repo.materials_out_of_stock_count(company_id=company_id),
                "warehouses_count": self.repo.active_warehouses_count(company_id=company_id),
            },
            "slabs_by_status": [{"status": s, "count": c} for s, c in status_counts.items()],
            "available_slabs_by_warehouse": [
                {"warehouse": w, "count": c}
                for w, c in self.repo.available_slabs_by_warehouse(company_id=company_id)
            ],
        }
