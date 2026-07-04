"""Flattens each analytics use case's result dict into a report-type-agnostic
shape the PDF and Excel generators can render without knowing anything about
Executive/Sales/Production/Installation/Finance specifically."""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Tuple

REPORT_TITLES = {
    "executive": "Executive Dashboard",
    "sales": "Sales Analytics",
    "production": "Production Analytics",
    "installation": "Installation Analytics",
    "finance": "Finance Analytics",
}

_KPI_LABELS = {
    # Executive
    "active_customers": "Active customers",
    "new_customers": "New customers",
    "lost_customers": "Lost customers",
    "leads_captured": "Leads captured",
    "leads_converted": "Leads converted",
    "lead_conversion_rate": "Lead conversion rate (%)",
    "quote_win_rate": "Quote win rate (%)",
    "orders_created": "Orders created",
    "revenue": "Revenue",
    "profit": "Profit",
    "profit_margin_pct": "Profit margin (%)",
    "orders_in_production": "Orders in production",
    "orders_awaiting_installation": "Orders awaiting installation",
    # Sales
    "total_quotes": "Total quotes",
    "accepted_quotes": "Accepted quotes",
    "win_rate": "Win rate (%)",
    "accepted_revenue": "Accepted revenue",
    "avg_quote_value": "Average quote value",
    # Production
    "orders_ready": "Orders ready",
    "orders_entered_production": "Orders entered production",
    "orders_completed_production": "Orders completed production",
    "avg_production_cycle_days": "Avg. production cycle (days)",
    # Installation
    "jobs_created": "Jobs created",
    "jobs_completed": "Jobs completed",
    "jobs_awaiting": "Jobs awaiting installation",
    "jobs_delayed": "Jobs delayed",
    "avg_delay_days": "Avg. delay (days)",
    "avg_installation_hours": "Avg. installation time (hours)",
    # Finance
    "cost": "Cost",
    "recognized_revenue": "Recognized revenue (completed orders)",
    "pipeline_value": "Pipeline value (in-progress orders)",
    "cancelled_value": "Cancelled value",
    "orders_count": "Orders",
}


@dataclass
class ExportTable:
    title: str
    headers: List[str]
    rows: List[List[str]]


@dataclass
class ExportSections:
    title: str
    date_from: str
    date_to: str
    kpis: List[Tuple[str, str]]
    tables: List[ExportTable] = field(default_factory=list)


def _fmt(value) -> str:
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    if isinstance(value, float):
        return f"{value:,.1f}"
    if value is None:
        return "—"
    return str(value)


def _kpis(data: dict) -> List[Tuple[str, str]]:
    return [(_KPI_LABELS.get(k, k.replace("_", " ").title()), _fmt(v)) for k, v in data["kpis"].items()]


def build_export_sections(report_type: str, data: dict) -> ExportSections:
    title = REPORT_TITLES.get(report_type, report_type.title())
    kpis = _kpis(data)
    tables: List[ExportTable] = []

    if report_type == "executive":
        tables.append(ExportTable("Customers by status", ["Status", "Count"],
                                   [[r["status"], str(r["count"])] for r in data["customers_by_status"]]))
        tables.append(ExportTable("Orders by status", ["Status", "Count"],
                                   [[r["status"], str(r["count"])] for r in data["orders_by_status"]]))
        tables.append(ExportTable("Revenue trend", ["Month", "Revenue", "Profit", "Orders"],
                                   [[r["month"], _fmt(r["revenue"]), _fmt(r["profit"]), str(r["count"])]
                                    for r in data["revenue_trend"]]))
    elif report_type == "sales":
        tables.append(ExportTable("Quotes by status", ["Status", "Count"],
                                   [[r["status"], str(r["count"])] for r in data["quotes_by_status"]]))
        tables.append(ExportTable("Revenue by project type", ["Project type", "Revenue"],
                                   [[r["project_type"], _fmt(r["revenue"])] for r in data["revenue_by_project_type"]]))
        tables.append(ExportTable("Top customers", ["Customer", "Revenue"],
                                   [[r["customer_name"], _fmt(r["revenue"])] for r in data["top_customers"]]))
    elif report_type == "production":
        tables.append(ExportTable("Order status breakdown", ["Status", "Count"],
                                   [[r["status"], str(r["count"])] for r in data["order_status_breakdown"]]))
        tables.append(ExportTable("Item status", ["Status", "Count"],
                                   [[r["status"], str(r["count"])] for r in data["item_production_status"]]))
    elif report_type == "installation":
        tables.append(ExportTable("Job status breakdown", ["Status", "Count"],
                                   [[r["status"], str(r["count"])] for r in data["job_status_breakdown"]]))
        tables.append(ExportTable("Daily installations", ["Date", "Count"],
                                   [[r["date"], str(r["count"])] for r in data["daily_installations"]]))
        tables.append(ExportTable("Crew productivity", ["Crew", "Completed", "Avg. hours"],
                                   [[r["crew_name"], str(r["completed_count"]), _fmt(r["avg_installation_hours"])]
                                    for r in data["crew_productivity"]]))
    elif report_type == "finance":
        tables.append(ExportTable("Monthly trend", ["Month", "Revenue", "Cost", "Profit", "Orders"],
                                   [[r["month"], _fmt(r["revenue"]), _fmt(r["cost"]), _fmt(r["profit"]), str(r["count"])]
                                    for r in data["monthly_trend"]]))
        tables.append(ExportTable("Revenue by currency", ["Currency", "Revenue"],
                                   [[r["currency"], _fmt(r["revenue"])] for r in data["revenue_by_currency"]]))

    return ExportSections(
        title=title,
        date_from=str(data["date_from"]),
        date_to=str(data["date_to"]),
        kpis=kpis,
        tables=tables,
    )
