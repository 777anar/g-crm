"""Sales Analytics: the Quote funnel -- win rate, revenue mix, top customers,
and a monthly trend of how quotes move through their lifecycle."""
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository
from modules.sales.domain.value_objects import VALID_QUOTE_STATUSES


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


class SalesAnalyticsUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        dr = data.date_range

        quote_counts = dict(self.repo.quote_status_counts(company_id=company_id, date_range=dr))
        total_quotes = sum(quote_counts.values())
        decided = quote_counts.get("accepted", 0) + quote_counts.get("rejected", 0) + quote_counts.get("expired", 0)
        win_rate = _pct(quote_counts.get("accepted", 0), decided)

        accepted_quotes = self.repo.accepted_quotes(company_id=company_id, date_range=dr)
        accepted_revenue = sum((q.total_final for q in accepted_quotes), Decimal("0"))
        avg_quote_value = (accepted_revenue / len(accepted_quotes)) if accepted_quotes else Decimal("0")

        revenue_by_type = self.repo.revenue_by_project_type(company_id=company_id, date_range=dr)
        top_customers = self.repo.top_customers_by_quote_value(company_id=company_id, date_range=dr, limit=5)

        quotes = self.repo.quotes_for_trend(company_id=company_id, date_range=dr)
        monthly: dict = defaultdict(lambda: {s: 0 for s in VALID_QUOTE_STATUSES})
        for q in quotes:
            month = q.created_at.strftime("%Y-%m")
            monthly[month][q.status] += 1
        monthly_trend = [{"month": m, **counts} for m, counts in sorted(monthly.items())]

        return {
            "date_from": dr.date_from,
            "date_to": dr.date_to,
            "kpis": {
                "total_quotes": total_quotes,
                "accepted_quotes": quote_counts.get("accepted", 0),
                "win_rate": win_rate,
                "accepted_revenue": accepted_revenue,
                "avg_quote_value": avg_quote_value,
            },
            "quotes_by_status": [{"status": s, "count": c} for s, c in quote_counts.items()],
            "revenue_by_project_type": [{"project_type": pt, "revenue": total} for pt, total in revenue_by_type],
            "top_customers": [
                {"customer_id": str(cid), "customer_name": name, "revenue": total}
                for cid, name, total in top_customers
            ],
            "monthly_trend": monthly_trend,
        }
