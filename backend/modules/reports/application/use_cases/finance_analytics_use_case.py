"""Finance Analytics: revenue, cost, and profit derived from the Orders
module's financial snapshot (copied from the accepted Quote at order-creation
time -- see modules/orders/application/use_cases/order_use_cases.py). There is
no dedicated Finance/invoicing module yet, so this reports on the real
monetary data Orders already carries rather than simulating invoices."""
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


class FinanceAnalyticsUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        dr = data.date_range

        orders = self.repo.orders_created_in_range(company_id=company_id, date_range=dr)

        revenue = sum((o.total_final for o in orders), Decimal("0"))
        cost = sum((o.total_internal_cost for o in orders), Decimal("0"))
        profit = sum((o.total_profit for o in orders), Decimal("0"))
        profit_margin_pct = float(round((profit / revenue) * 100, 1)) if revenue else 0.0

        recognized_revenue = sum((o.total_final for o in orders if o.status == "completed"), Decimal("0"))
        cancelled_value = sum((o.total_final for o in orders if o.status == "cancelled"), Decimal("0"))
        pipeline_value = sum(
            (o.total_final for o in orders if o.status not in ("completed", "cancelled")), Decimal("0")
        )

        monthly_trend = ReportsRepository.group_monthly(
            orders, date_field="created_at", value_fields=("total_final", "total_internal_cost", "total_profit")
        )

        by_currency: dict = defaultdict(lambda: Decimal("0"))
        for o in orders:
            by_currency[o.currency] += o.total_final

        return {
            "date_from": dr.date_from,
            "date_to": dr.date_to,
            "kpis": {
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "profit_margin_pct": profit_margin_pct,
                "recognized_revenue": recognized_revenue,
                "pipeline_value": pipeline_value,
                "cancelled_value": cancelled_value,
                "orders_count": len(orders),
            },
            "monthly_trend": [
                {
                    "month": r["month"],
                    "revenue": r["total_final"],
                    "cost": r["total_internal_cost"],
                    "profit": r["total_profit"],
                    "count": r["count"],
                }
                for r in monthly_trend
            ],
            "revenue_by_currency": [{"currency": c, "revenue": v} for c, v in by_currency.items()],
        }
