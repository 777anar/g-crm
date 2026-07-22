"""Production Planning Dashboard (Phase 2 requirement #5): a live,
not-date-ranged snapshot -- like Inventory Analytics -- of every work
order still on the shop floor, grouped by its configurable stage,
alongside per-operator workload and overdue highlighting. Reads
Production's `work_orders`/`production_stages` tables directly, the same
"Reports imports other modules' models straight, no repository-of-a-
repository" pattern every other analytics use case here already uses."""
from datetime import date as date_cls
from decimal import Decimal

from sqlalchemy.orm import Session

from modules.production.infrastructure.repositories.production_stage_repository import ProductionStageRepository
from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


class ProductionPlanningUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)
        self.stages_repo = ProductionStageRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        today = date_cls.today().isoformat()

        # Same lazy-seed as `GET /production/stages` -- a company that has
        # never opened the Stages settings page yet should still see a
        # real, usable dashboard, not an empty stage list.
        stages = self.stages_repo.list_or_seed_defaults(company_id=company_id)
        stage_name_by_id = {str(s.id): s.name for s in stages}

        rows = self.repo.active_work_orders_with_order_and_customer(company_id=company_id)
        operator_ids = {str(wo.assigned_to) for wo, _, _ in rows if wo.assigned_to}
        operator_names = self.repo.user_names_by_id(company_id=company_id, user_ids=list(operator_ids))

        jobs = []
        overdue_count = 0
        workload: dict = {}
        for wo, order, customer in rows:
            is_overdue = bool(wo.scheduled_completion_date and wo.scheduled_completion_date < today)
            if is_overdue:
                overdue_count += 1

            job = {
                "id": str(wo.id),
                "work_order_number": wo.work_order_number,
                "order_id": str(order.id),
                "order_number": order.order_number,
                "customer_name": customer.name if customer else None,
                "status": wo.status,
                "priority": wo.priority,
                "stage_id": str(wo.current_stage_id) if wo.current_stage_id else None,
                "stage_name": stage_name_by_id.get(str(wo.current_stage_id)) if wo.current_stage_id else None,
                "assigned_to": str(wo.assigned_to) if wo.assigned_to else None,
                "assigned_operator_name": operator_names.get(str(wo.assigned_to)) if wo.assigned_to else None,
                "due_date": wo.scheduled_completion_date,
                "is_overdue": is_overdue,
            }
            jobs.append(job)

            if wo.assigned_to:
                key = str(wo.assigned_to)
                bucket = workload.setdefault(key, {
                    "operator_id": key,
                    "operator_name": operator_names.get(key, key),
                    "job_count": 0,
                    "overdue_count": 0,
                })
                bucket["job_count"] += 1
                if is_overdue:
                    bucket["overdue_count"] += 1

        return {
            "stages": [{"id": str(s.id), "name": s.name, "sort_order": s.sort_order} for s in stages],
            "jobs": jobs,
            "operator_workload": sorted(workload.values(), key=lambda w: -w["job_count"]),
            "overdue_count": overdue_count,
            "total_active_jobs": len(jobs),
        }
