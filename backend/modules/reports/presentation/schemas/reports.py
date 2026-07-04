from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class MonthlyPoint(BaseModel):
    month: str
    count: int


# ── Executive Dashboard ──────────────────────────────────────────────────────

class ExecutiveKpis(BaseModel):
    active_customers: int
    new_customers: int
    lost_customers: int
    leads_captured: int
    leads_converted: int
    lead_conversion_rate: float
    quote_win_rate: float
    orders_created: int
    revenue: Decimal
    profit: Decimal
    profit_margin_pct: float
    orders_in_production: int
    orders_awaiting_installation: int


class ExecutiveRevenuePoint(BaseModel):
    month: str
    revenue: Decimal
    profit: Decimal
    count: int


class ExecutiveDashboardOut(BaseModel):
    date_from: date
    date_to: date
    kpis: ExecutiveKpis
    customers_by_status: List[StatusCount]
    orders_by_status: List[StatusCount]
    revenue_trend: List[ExecutiveRevenuePoint]


# ── Sales Analytics ──────────────────────────────────────────────────────────

class SalesKpis(BaseModel):
    total_quotes: int
    accepted_quotes: int
    win_rate: float
    accepted_revenue: Decimal
    avg_quote_value: Decimal


class RevenueByProjectType(BaseModel):
    project_type: str
    revenue: Decimal


class TopCustomer(BaseModel):
    customer_id: str
    customer_name: str
    revenue: Decimal


class SalesMonthlyPoint(BaseModel):
    month: str
    draft: int = 0
    sent: int = 0
    negotiation: int = 0
    accepted: int = 0
    rejected: int = 0
    expired: int = 0


class SalesAnalyticsOut(BaseModel):
    date_from: date
    date_to: date
    kpis: SalesKpis
    quotes_by_status: List[StatusCount]
    revenue_by_project_type: List[RevenueByProjectType]
    top_customers: List[TopCustomer]
    monthly_trend: List[SalesMonthlyPoint]


# ── Production Analytics ─────────────────────────────────────────────────────

class ProductionKpis(BaseModel):
    orders_in_production: int
    orders_ready: int
    orders_entered_production: int
    orders_completed_production: int
    avg_production_cycle_days: Optional[float]


class ProductionAnalyticsOut(BaseModel):
    date_from: date
    date_to: date
    kpis: ProductionKpis
    order_status_breakdown: List[StatusCount]
    item_production_status: List[StatusCount]


# ── Installation Analytics ───────────────────────────────────────────────────

class InstallationKpis(BaseModel):
    orders_awaiting_installation: int
    orders_installed: int
    avg_installation_cycle_days: Optional[float]


class InstallationAnalyticsOut(BaseModel):
    date_from: date
    date_to: date
    kpis: InstallationKpis
    order_status_breakdown: List[StatusCount]
    item_installation_status: List[StatusCount]


# ── Finance Analytics ─────────────────────────────────────────────────────────

class FinanceKpis(BaseModel):
    revenue: Decimal
    cost: Decimal
    profit: Decimal
    profit_margin_pct: float
    recognized_revenue: Decimal
    pipeline_value: Decimal
    cancelled_value: Decimal
    orders_count: int


class FinanceMonthlyPoint(BaseModel):
    month: str
    revenue: Decimal
    cost: Decimal
    profit: Decimal
    count: int


class RevenueByCurrency(BaseModel):
    currency: str
    revenue: Decimal


class FinanceAnalyticsOut(BaseModel):
    date_from: date
    date_to: date
    kpis: FinanceKpis
    monthly_trend: List[FinanceMonthlyPoint]
    revenue_by_currency: List[RevenueByCurrency]
