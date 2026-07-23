"""phase18_postgres_row_level_security

Revision ID: 55d19b5b6862
Revises: f39076f4e8fa
Create Date: 2026-07-23 09:05:00.000000

Enables Postgres Row-Level Security on every tenant-owned (`company_id`)
table, per MASTER_DEVELOPMENT_ROADMAP.md Phase 18 and DATABASE_DESIGN.md
section 7's documented (previously unimplemented) "defense-in-depth second
tenancy layer." No-ops entirely on SQLite (dev/test), which has no RLS
concept -- see core/db/mixins.py's `CompanyScopedMixin` docstring and
core/db/session.py's `set_company_context`/`_apply_rls_company_context`,
which populate `current_setting('app.current_company_id')` per-request via
core/api/middleware.py's `CompanyContextMiddleware`.

Deliberately `ENABLE` (not `FORCE`) ROW LEVEL SECURITY: Postgres exempts a
table's owning role from RLS restrictions unless FORCE is also applied, so
migrations/seed scripts run by that owning role are unaffected without
needing to set the session variable themselves. Full efficacy in production
requires the application's runtime connection to use a *non-owner* Postgres
role -- an operational/infra step outside this migration's scope, tracked
alongside it rather than silently assumed. Until that role separation
exists, application-layer `company_id` filtering (already present in every
repository) remains the primary tenant-isolation guarantee; this migration
adds the second layer on top of it, not instead of it.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '55d19b5b6862'
down_revision: Union[str, None] = 'f39076f4e8fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every tenant-scoped table (has a `company_id` column), core and module
# alike. `communication_integration_logs.company_id` is nullable (system-level
# integration logs can have no company), so it gets a slightly different
# USING clause below; every other table uses the standard equality policy.
_TENANT_TABLES = [
    # core
    "audit_log",
    "event_log",
    "documents",
    "ai_jobs",
    "user_company_roles",
    "audit_retention_policies",
    # crm
    "crm_customers",
    "crm_leads",
    "crm_contacts",
    "crm_activities",
    "crm_tasks",
    "crm_task_notifications",
    # catalog
    "catalog_collections",
    "catalog_warehouses",
    "catalog_brands",
    "catalog_slab_reservations",
    "catalog_materials",
    "catalog_material_sizes",
    "catalog_slabs",
    "catalog_material_images",
    "catalog_material_thicknesses",
    "catalog_material_documents",
    "catalog_price_lists",
    "catalog_price_list_entries",
    # sales
    "sales_rooms",
    "sales_quote_section_measurements",
    "sales_quote_section_items",
    "sales_quote_sections",
    "sales_quote_number_sequences",
    "sales_project_items",
    "sales_quotes",
    "sales_projects",
    "sales_project_item_photos",
    "company_service_prices",
    "sales_project_item_measurements",
    "sales_project_item_drawings",
    # orders
    "order_measurements",
    "order_items",
    "orders",
    "order_number_sequences",
    "order_sections",
    # production
    "work_orders",
    "work_order_events",
    "production_stages",
    "work_order_items",
    "work_order_number_sequences",
    # installation
    "installation_notifications",
    "installation_photos",
    "installation_job_number_sequences",
    "installation_jobs",
    "installation_crew_members",
    "installation_crews",
    # finance
    "invoice_payments",
    "invoice_number_sequences",
    "invoice_lines",
    "invoices",
    "expenses",
    # purchasing
    "purchase_orders",
    "goods_receipts",
    "purchase_order_lines",
    "purchase_order_number_sequences",
    "suppliers",
    # communication (see _NULLABLE_COMPANY_TABLES below)
    "communication_channel_credentials",
    "communication_conversations",
    "communication_channels",
    "communication_conversation_notes",
    "communication_message_attachments",
    "communication_message_templates",
    "communication_message_queue",
    "communication_integration_logs",
    "communication_messages",
    # ai
    "ai_recommendations",
    # marketing
    "campaigns",
    # customer_portal
    "customer_portal_logins",
    # cut_optimization
    "cut_optimization_runs",
]

_NULLABLE_COMPANY_TABLES = {"communication_integration_logs"}

_POLICY_NAME = "company_isolation"


def _using_clause(table: str) -> str:
    if table in _NULLABLE_COMPANY_TABLES:
        return "(company_id IS NULL OR company_id = current_setting('app.current_company_id', true)::uuid)"
    return "company_id = current_setting('app.current_company_id', true)::uuid"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _TENANT_TABLES:
        using = _using_clause(table)
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY {_POLICY_NAME} ON "{table}" '
            f'USING ({using}) WITH CHECK ({using})'
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _TENANT_TABLES:
        op.execute(f'DROP POLICY IF EXISTS {_POLICY_NAME} ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
