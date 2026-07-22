"""Read-only cross-module aggregation queries for the Reports module.

Reports owns no tables of its own -- every query here reads existing
CRM/Sales/Orders tables (plus the shared audit log for status-change
history), always scoped by company_id. Month-bucketed trends are grouped
in Python rather than SQL (`strftime` vs `date_trunc` differ by dialect,
and this repository must work against both SQLite in tests and Postgres
in production).
"""
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.audit.models import AuditLog
from core.auth.models import User
from modules.catalog.domain.value_objects import MATERIAL_STATUS_ACTIVE, SLAB_STATUS_AVAILABLE
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.catalog.infrastructure.models.slab import Slab
from modules.catalog.infrastructure.models.warehouse import Warehouse
from modules.crm.infrastructure.models.customer import Customer
from modules.crm.infrastructure.models.lead import Lead
from modules.installation.infrastructure.models.crew import Crew
from modules.installation.infrastructure.models.installation_job import InstallationJob
from modules.orders.infrastructure.models.order import Order
from modules.orders.infrastructure.models.order_item import OrderItem
from modules.production.domain.value_objects import TERMINAL_WORK_ORDER_STATUSES
from modules.production.infrastructure.models.work_order import WorkOrder
from modules.reports.domain.value_objects import DateRange
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.models.quote import Quote


def _day_bounds(date_range: DateRange) -> Tuple[datetime, datetime]:
    start = datetime.combine(date_range.date_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_range.date_to, time.max, tzinfo=timezone.utc)
    return start, end


class ReportsRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── CRM ───────────────────────────────────────────────────────────────────

    def customer_status_snapshot(self, *, company_id: uuid.UUID) -> List[Tuple[str, int]]:
        """Current distribution of active (non-archived) customers by pipeline status."""
        stmt = (
            select(Customer.status, func.count(Customer.id))
            .where(Customer.company_id == company_id, Customer.deleted_at.is_(None))
            .group_by(Customer.status)
        )
        return list(self.db.execute(stmt).all())

    def new_customers_count(self, *, company_id: uuid.UUID, date_range: DateRange) -> int:
        start, end = _day_bounds(date_range)
        stmt = select(func.count(Customer.id)).where(
            Customer.company_id == company_id,
            Customer.created_at.between(start, end),
        )
        return self.db.scalar(stmt) or 0

    def lost_customers_count(self, *, company_id: uuid.UUID, date_range: DateRange) -> int:
        start, end = _day_bounds(date_range)
        stmt = select(func.count(Customer.id)).where(
            Customer.company_id == company_id,
            Customer.status == "lost",
            Customer.updated_at.between(start, end),
        )
        return self.db.scalar(stmt) or 0

    def lead_status_counts(self, *, company_id: uuid.UUID, date_range: DateRange) -> List[Tuple[str, int]]:
        start, end = _day_bounds(date_range)
        stmt = (
            select(Lead.status, func.count(Lead.id))
            .where(Lead.company_id == company_id, Lead.created_at.between(start, end))
            .group_by(Lead.status)
        )
        return list(self.db.execute(stmt).all())

    def leads_converted_count(self, *, company_id: uuid.UUID, date_range: DateRange) -> int:
        start, end = _day_bounds(date_range)
        stmt = select(func.count(Lead.id)).where(
            Lead.company_id == company_id,
            Lead.converted_at.is_not(None),
            Lead.converted_at.between(start, end),
        )
        return self.db.scalar(stmt) or 0

    # ── Sales (Quotes) ───────────────────────────────────────────────────────

    def quote_status_counts(self, *, company_id: uuid.UUID, date_range: DateRange) -> List[Tuple[str, int]]:
        start, end = _day_bounds(date_range)
        stmt = (
            select(Quote.status, func.count(Quote.id))
            .where(Quote.company_id == company_id, Quote.created_at.between(start, end))
            .group_by(Quote.status)
        )
        return list(self.db.execute(stmt).all())

    def accepted_quotes(self, *, company_id: uuid.UUID, date_range: DateRange) -> List[Quote]:
        start, end = _day_bounds(date_range)
        stmt = select(Quote).where(
            Quote.company_id == company_id,
            Quote.status == "accepted",
            Quote.created_at.between(start, end),
        )
        return list(self.db.scalars(stmt).all())

    def revenue_by_project_type(
        self, *, company_id: uuid.UUID, date_range: DateRange
    ) -> List[Tuple[str, Decimal]]:
        start, end = _day_bounds(date_range)
        stmt = (
            select(Project.project_type, func.sum(Quote.total_final))
            .join(Project, Project.id == Quote.project_id)
            .where(
                Quote.company_id == company_id,
                Quote.status == "accepted",
                Quote.created_at.between(start, end),
            )
            .group_by(Project.project_type)
        )
        return [(pt or "other", total or Decimal("0")) for pt, total in self.db.execute(stmt).all()]

    def top_customers_by_quote_value(
        self, *, company_id: uuid.UUID, date_range: DateRange, limit: int = 5
    ) -> List[Tuple[uuid.UUID, str, Decimal]]:
        start, end = _day_bounds(date_range)
        stmt = (
            select(Customer.id, Customer.name, func.sum(Quote.total_final).label("total"))
            .join(Customer, Customer.id == Quote.customer_id)
            .where(
                Quote.company_id == company_id,
                Quote.status == "accepted",
                Quote.created_at.between(start, end),
            )
            .group_by(Customer.id, Customer.name)
            .order_by(func.sum(Quote.total_final).desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).all())

    def quotes_for_trend(self, *, company_id: uuid.UUID, date_range: DateRange) -> List[Quote]:
        start, end = _day_bounds(date_range)
        stmt = select(Quote).where(Quote.company_id == company_id, Quote.created_at.between(start, end))
        return list(self.db.scalars(stmt).all())

    # ── Orders (Production / Installation / Finance) ─────────────────────────

    def order_status_snapshot(self, *, company_id: uuid.UUID) -> List[Tuple[str, int]]:
        """Current distribution of every order by lifecycle status, regardless
        of the report's date range -- this is a live operational snapshot."""
        stmt = select(Order.status, func.count(Order.id)).where(Order.company_id == company_id).group_by(Order.status)
        return list(self.db.execute(stmt).all())

    def orders_created_in_range(self, *, company_id: uuid.UUID, date_range: DateRange) -> List[Order]:
        start, end = _day_bounds(date_range)
        stmt = select(Order).where(Order.company_id == company_id, Order.created_at.between(start, end))
        return list(self.db.scalars(stmt).all())

    def order_item_status_counts(
        self, *, company_id: uuid.UUID, field: str
    ) -> List[Tuple[Optional[str], int]]:
        """`field` is either 'production_status' or 'installation_status' -- the
        live per-item shop-floor/install status, not date-bound."""
        column = getattr(OrderItem, field)
        stmt = (
            select(column, func.count(OrderItem.id))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.company_id == company_id)
            .group_by(column)
        )
        return list(self.db.execute(stmt).all())

    def order_status_change_timestamps(
        self, *, company_id: uuid.UUID, date_range: DateRange
    ) -> Dict[str, Dict[str, datetime]]:
        """For every order created within the range, the timestamp it first
        entered each status it has passed through -- derived from the audit
        log's `order.status_changed` entries (see modules/orders/application/
        use_cases/order_use_cases.py). Real history, not a fabricated metric."""
        orders = self.orders_created_in_range(company_id=company_id, date_range=date_range)
        order_ids = [o.id for o in orders]
        if not order_ids:
            return {}

        stmt = select(AuditLog).where(
            AuditLog.company_id == company_id,
            AuditLog.entity_type == "order",
            AuditLog.action == "order.status_changed",
            AuditLog.entity_id.in_(order_ids),
        )
        rows = self.db.scalars(stmt).all()

        timestamps: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        for row in rows:
            new_status = (row.diff_json or {}).get("status", {}).get("new")
            if not new_status:
                continue
            entity_id = str(row.entity_id)
            # First occurrence wins -- a status can only meaningfully be "entered" once
            # for cycle-time purposes (re-entry after a correction is rare and would
            # otherwise skew the average toward the latest, not the real, transition).
            if new_status not in timestamps[entity_id]:
                timestamps[entity_id][new_status] = row.created_at
        return dict(timestamps)

    @staticmethod
    def group_monthly(items, *, date_field: str, value_fields: Tuple[str, ...]) -> List[dict]:
        """Groups a list of ORM rows into `{month, <value_field>: total, ...}`
        buckets by calendar month, done in Python so the same code works
        against SQLite (tests) and Postgres (production) without relying on
        dialect-specific date-truncation SQL."""
        buckets: Dict[str, Dict[str, Decimal]] = defaultdict(lambda: {f: Decimal("0") for f in value_fields})
        counts: Dict[str, int] = defaultdict(int)
        for item in items:
            month = getattr(item, date_field).strftime("%Y-%m")
            counts[month] += 1
            for field in value_fields:
                buckets[month][field] += getattr(item, field) or Decimal("0")
        return [
            {"month": month, "count": counts[month], **buckets[month]}
            for month in sorted(buckets.keys())
        ]

    # ── Installation (real module data, not an Orders proxy) ─────────────────

    def installation_jobs_created_in_range(
        self, *, company_id: uuid.UUID, date_range: DateRange
    ) -> List[InstallationJob]:
        start, end = _day_bounds(date_range)
        stmt = select(InstallationJob).where(
            InstallationJob.company_id == company_id, InstallationJob.created_at.between(start, end)
        )
        return list(self.db.scalars(stmt).all())

    def installation_job_status_snapshot(self, *, company_id: uuid.UUID) -> List[Tuple[str, int]]:
        stmt = (
            select(InstallationJob.status, func.count(InstallationJob.id))
            .where(InstallationJob.company_id == company_id)
            .group_by(InstallationJob.status)
        )
        return list(self.db.execute(stmt).all())

    def crew_names_by_id(self, *, company_id: uuid.UUID) -> Dict[str, str]:
        stmt = select(Crew.id, Crew.name).where(Crew.company_id == company_id)
        return {str(crew_id): name for crew_id, name in self.db.execute(stmt).all()}

    # ── Catalog (Inventory) ───────────────────────────────────────────────────

    def slab_status_snapshot(self, *, company_id: uuid.UUID) -> List[Tuple[str, int]]:
        """Current distribution of every tracked slab by lifecycle status --
        a live stock snapshot, not date-bound, mirroring order_status_snapshot."""
        stmt = select(Slab.status, func.count(Slab.id)).where(Slab.company_id == company_id).group_by(Slab.status)
        return list(self.db.execute(stmt).all())

    def available_slab_area_m2(self, *, company_id: uuid.UUID) -> Decimal:
        """Total area of stock that is actually sellable right now -- slabs
        already reserved/sold/in production/scrapped don't count."""
        stmt = select(func.sum(Slab.area_m2)).where(
            Slab.company_id == company_id, Slab.status == SLAB_STATUS_AVAILABLE
        )
        return self.db.scalar(stmt) or Decimal("0")

    def available_slabs_by_warehouse(self, *, company_id: uuid.UUID) -> List[Tuple[str, int]]:
        stmt = (
            select(Warehouse.name, func.count(Slab.id))
            .join(Slab, Slab.warehouse_id == Warehouse.id)
            .where(Slab.company_id == company_id, Slab.status == SLAB_STATUS_AVAILABLE)
            .group_by(Warehouse.name)
        )
        return list(self.db.execute(stmt).all())

    def materials_tracked_count(self, *, company_id: uuid.UUID) -> int:
        stmt = select(func.count(StoneMaterial.id)).where(
            StoneMaterial.company_id == company_id, StoneMaterial.status == MATERIAL_STATUS_ACTIVE
        )
        return self.db.scalar(stmt) or 0

    def materials_out_of_stock_count(self, *, company_id: uuid.UUID) -> int:
        """Active, sellable materials with zero slabs currently available --
        the "what can I not quote right now" signal. No stock-threshold field
        exists on Material, so this reports a real, computable zero rather
        than a fabricated low-stock cutoff."""
        available_material_ids = select(Slab.material_id).where(
            Slab.company_id == company_id, Slab.status == SLAB_STATUS_AVAILABLE
        )
        stmt = select(func.count(StoneMaterial.id)).where(
            StoneMaterial.company_id == company_id,
            StoneMaterial.status == MATERIAL_STATUS_ACTIVE,
            StoneMaterial.id.notin_(available_material_ids),
        )
        return self.db.scalar(stmt) or 0

    def active_warehouses_count(self, *, company_id: uuid.UUID) -> int:
        stmt = select(func.count(Warehouse.id)).where(
            Warehouse.company_id == company_id, Warehouse.status == "active"
        )
        return self.db.scalar(stmt) or 0

    # ── Production Planning Dashboard (Phase 2) ────────────────────────────────

    def active_work_orders_with_order_and_customer(
        self, *, company_id: uuid.UUID
    ) -> List[Tuple[WorkOrder, Order, Optional[Customer]]]:
        """Every work order not yet completed/cancelled -- the Production
        Planning Dashboard's whole subject -- joined with its Order (for
        the order number) and Customer (for a human-readable name), the
        same enrichment shape Production's own `GET /production/{id}/job`
        endpoint already assembles for a single job, here done for all of
        them at once."""
        stmt = (
            select(WorkOrder, Order, Customer)
            .join(Order, Order.id == WorkOrder.order_id)
            .outerjoin(Customer, Customer.id == Order.customer_id)
            .where(
                WorkOrder.company_id == company_id,
                WorkOrder.status.notin_(TERMINAL_WORK_ORDER_STATUSES),
            )
        )
        return list(self.db.execute(stmt).all())

    def user_names_by_id(self, *, company_id: uuid.UUID, user_ids) -> Dict[str, str]:
        if not user_ids:
            return {}
        stmt = select(User.id, User.full_name).where(User.id.in_(user_ids))
        return {str(user_id): name for user_id, name in self.db.execute(stmt).all()}
