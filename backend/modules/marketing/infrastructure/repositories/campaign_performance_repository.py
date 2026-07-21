"""Read-only cross-module aggregation for campaign performance/attribution.

Marketing owns no data in CRM or Orders -- this repository reads
`crm_leads` (filtered by the opaque `campaign_id` reference every lead
captured under a campaign carries) and, for leads that converted, the
resulting customer's `orders` to attribute real revenue back to the
campaign that brought the lead in. Same "reads other modules' tables
directly, always company_id-scoped" pattern Reports already established
(`modules/reports/infrastructure/repositories/reports_repository.py`) --
Marketing does not own these tables, it only ever reads them.
"""
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.crm.infrastructure.models.lead import Lead
from modules.marketing.domain.value_objects import ORDER_STATUSES_COUNTED_AS_REVENUE
from modules.orders.infrastructure.models.order import Order


@dataclass
class CampaignPerformance:
    leads_count: int
    converted_count: int
    conversion_rate: float
    attributed_revenue: Decimal


class CampaignPerformanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_performance(self, *, company_id: uuid.UUID, campaign_id: uuid.UUID) -> CampaignPerformance:
        leads: List[Lead] = list(
            self.db.scalars(
                select(Lead).where(Lead.company_id == company_id, Lead.campaign_id == campaign_id)
            ).all()
        )
        leads_count = len(leads)
        converted_customer_ids = [lead.converted_customer_id for lead in leads if lead.converted_customer_id]
        converted_count = len(converted_customer_ids)
        conversion_rate = (converted_count / leads_count) if leads_count else 0.0

        attributed_revenue = Decimal("0")
        if converted_customer_ids:
            orders: List[Order] = list(
                self.db.scalars(
                    select(Order).where(
                        Order.company_id == company_id,
                        Order.customer_id.in_(converted_customer_ids),
                        Order.status.in_(ORDER_STATUSES_COUNTED_AS_REVENUE),
                    )
                ).all()
            )
            for order in orders:
                attributed_revenue += Decimal(order.total_final)

        return CampaignPerformance(
            leads_count=leads_count,
            converted_count=converted_count,
            conversion_rate=conversion_rate,
            attributed_revenue=attributed_revenue,
        )
