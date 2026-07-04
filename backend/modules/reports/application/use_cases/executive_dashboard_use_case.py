"""Executive Dashboard: the cross-module KPI summary -- one screen answering
"how is the business doing right now" by pulling from CRM, Sales, and Orders."""
from decimal import Decimal

from sqlalchemy.orm import Session

from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


class ExecutiveDashboardUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        dr = data.date_range

        customers_by_status = self.repo.customer_status_snapshot(company_id=company_id)
        active_customers = sum(count for _, count in customers_by_status)
        new_customers = self.repo.new_customers_count(company_id=company_id, date_range=dr)
        lost_customers = self.repo.lost_customers_count(company_id=company_id, date_range=dr)

        lead_counts = dict(self.repo.lead_status_counts(company_id=company_id, date_range=dr))
        leads_captured = sum(lead_counts.values())
        leads_converted = self.repo.leads_converted_count(company_id=company_id, date_range=dr)

        quote_counts = dict(self.repo.quote_status_counts(company_id=company_id, date_range=dr))
        decided_quotes = quote_counts.get("accepted", 0) + quote_counts.get("rejected", 0) + quote_counts.get("expired", 0)
        quote_win_rate = _pct(quote_counts.get("accepted", 0), decided_quotes)

        orders_by_status = self.repo.order_status_snapshot(company_id=company_id)
        orders_by_status_map = dict(orders_by_status)
        orders_in_production = orders_by_status_map.get("in_production", 0)
        orders_awaiting_installation = orders_by_status_map.get("ready", 0) + orders_by_status_map.get("delivered", 0)

        orders_in_range = self.repo.orders_created_in_range(company_id=company_id, date_range=dr)
        orders_created = len(orders_in_range)
        revenue = sum((o.total_final for o in orders_in_range), Decimal("0"))
        profit = sum((o.total_profit for o in orders_in_range), Decimal("0"))
        profit_margin_pct = float(round((profit / revenue) * 100, 1)) if revenue else 0.0

        revenue_trend = ReportsRepository.group_monthly(
            orders_in_range, date_field="created_at", value_fields=("total_final", "total_profit")
        )

        return {
            "date_from": dr.date_from,
            "date_to": dr.date_to,
            "kpis": {
                "active_customers": active_customers,
                "new_customers": new_customers,
                "lost_customers": lost_customers,
                "leads_captured": leads_captured,
                "leads_converted": leads_converted,
                "lead_conversion_rate": _pct(leads_converted, leads_captured),
                "quote_win_rate": quote_win_rate,
                "orders_created": orders_created,
                "revenue": revenue,
                "profit": profit,
                "profit_margin_pct": profit_margin_pct,
                "orders_in_production": orders_in_production,
                "orders_awaiting_installation": orders_awaiting_installation,
            },
            "customers_by_status": [{"status": s, "count": c} for s, c in customers_by_status],
            "orders_by_status": [{"status": s, "count": c} for s, c in orders_by_status],
            "revenue_trend": [
                {"month": r["month"], "revenue": r["total_final"], "profit": r["total_profit"], "count": r["count"]}
                for r in revenue_trend
            ],
        }
