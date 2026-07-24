import uuid
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
    jobs_created: int
    jobs_completed: int
    jobs_awaiting: int
    jobs_delayed: int
    avg_delay_days: Optional[float]
    avg_installation_hours: Optional[float]


class DailyInstallationPoint(BaseModel):
    date: str
    count: int


class CrewProductivity(BaseModel):
    crew_id: str
    crew_name: str
    completed_count: int
    avg_installation_hours: Optional[float]


class InstallationAnalyticsOut(BaseModel):
    date_from: date
    date_to: date
    kpis: InstallationKpis
    job_status_breakdown: List[StatusCount]
    daily_installations: List[DailyInstallationPoint]
    crew_productivity: List[CrewProductivity]


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
    purchase_cost: Decimal
    supplier_payments: Decimal
    supplier_payables: Decimal


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


# ── Inventory Analytics ──────────────────────────────────────────────────────

class InventoryKpis(BaseModel):
    total_slabs: int
    available_slabs: int
    reserved_slabs: int
    in_production_slabs: int
    sold_slabs: int
    available_area_m2: Decimal
    materials_tracked: int
    materials_out_of_stock: int
    warehouses_count: int


class WarehouseCount(BaseModel):
    warehouse: str
    count: int


class InventoryAnalyticsOut(BaseModel):
    date_from: date
    date_to: date
    kpis: InventoryKpis
    slabs_by_status: List[StatusCount]
    available_slabs_by_warehouse: List[WarehouseCount]


# ── Automated low-stock -> purchase suggestion (Phase 20) ────────────────────


class LowStockMaterialOut(BaseModel):
    material_id: uuid.UUID
    material_name: str
    brand_name: str
    available_slab_count: int
    available_area_m2: Decimal
    no_fit_recommendation_count: int
    suggested: bool


class LowStockSuggestionsOut(BaseModel):
    stock_threshold: int
    no_fit_window_days: int
    no_fit_threshold: int
    materials: List[LowStockMaterialOut]


# ── Production Planning Dashboard (Phase 2) ──────────────────────────────────

class ProductionPlanningStageOut(BaseModel):
    id: str
    name: str
    sort_order: int


class ProductionPlanningJobOut(BaseModel):
    id: str
    work_order_number: str
    order_id: str
    order_number: str
    customer_name: Optional[str]
    status: str
    priority: str
    stage_id: Optional[str]
    stage_name: Optional[str]
    assigned_to: Optional[str]
    assigned_operator_name: Optional[str]
    due_date: Optional[str]
    is_overdue: bool


class OperatorWorkloadOut(BaseModel):
    operator_id: str
    operator_name: str
    job_count: int
    overdue_count: int


class ProductionPlanningOut(BaseModel):
    stages: List[ProductionPlanningStageOut]
    jobs: List[ProductionPlanningJobOut]
    operator_workload: List[OperatorWorkloadOut]
    overdue_count: int
    total_active_jobs: int
