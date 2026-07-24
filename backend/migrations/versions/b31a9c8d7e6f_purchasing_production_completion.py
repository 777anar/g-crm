"""Purchasing production completion: procurement lifecycle.

Revision ID: b31a9c8d7e6f
Revises: e12a7189e238
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core.db.mixins

revision: str = "b31a9c8d7e6f"
down_revision: Union[str, None] = "e12a7189e238"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("tax_id", sa.String(100), nullable=True))
    op.add_column("suppliers", sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("suppliers", sa.Column("default_currency", sa.String(3), nullable=False, server_default="AZN"))
    op.add_column("suppliers", sa.Column("rating", sa.Numeric(3, 2), nullable=False, server_default="0"))
    op.create_table("supplier_contacts",
        sa.Column("company_id", core.db.mixins.GUID(), nullable=False), sa.Column("supplier_id", core.db.mixins.GUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False), sa.Column("job_title", sa.String(120)), sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(80)), sa.Column("is_primary", sa.Boolean(), nullable=False), sa.Column("id", core.db.mixins.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"],["companies.id"]), sa.ForeignKeyConstraint(["supplier_id"],["suppliers.id"]), sa.PrimaryKeyConstraint("id"))
    for col in ("company_id","supplier_id"): op.create_index(f"ix_supplier_contacts_{col}","supplier_contacts",[col])
    op.create_table("purchase_rfqs",
        sa.Column("company_id",core.db.mixins.GUID(),nullable=False),sa.Column("supplier_id",core.db.mixins.GUID(),nullable=False),
        sa.Column("rfq_number",sa.String(50),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("currency",sa.String(3),nullable=False),
        sa.Column("response_due_date",sa.String(10)),sa.Column("quoted_total",sa.Numeric(14,2)),sa.Column("supplier_reference",sa.String(120)),
        sa.Column("notes",sa.Text()),sa.Column("created_by",core.db.mixins.GUID(),nullable=False),sa.Column("id",core.db.mixins.GUID(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["company_id"],["companies.id"]),sa.ForeignKeyConstraint(["supplier_id"],["suppliers.id"]),
        sa.ForeignKeyConstraint(["created_by"],["users.id"]),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("company_id","rfq_number",name="uq_purchase_rfq_number"))
    for col in ("company_id","supplier_id","rfq_number","status"): op.create_index(f"ix_purchase_rfqs_{col}","purchase_rfqs",[col])
    op.create_table("purchase_rfq_lines",
        sa.Column("company_id",core.db.mixins.GUID(),nullable=False),sa.Column("rfq_id",core.db.mixins.GUID(),nullable=False),
        sa.Column("material_id",core.db.mixins.GUID()),sa.Column("description",sa.String(500),nullable=False),sa.Column("quantity",sa.Numeric(10,3),nullable=False),
        sa.Column("unit",sa.String(20),nullable=False),sa.Column("quoted_unit_cost",sa.Numeric(14,2)),sa.Column("sort_order",sa.Integer(),nullable=False),
        sa.Column("id",core.db.mixins.GUID(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["company_id"],["companies.id"]),sa.ForeignKeyConstraint(["rfq_id"],["purchase_rfqs.id"]),
        sa.ForeignKeyConstraint(["material_id"],["catalog_materials.id"]),sa.PrimaryKeyConstraint("id"))
    for col in ("company_id","rfq_id","material_id"): op.create_index(f"ix_purchase_rfq_lines_{col}","purchase_rfq_lines",[col])
    with op.batch_alter_table("purchase_orders") as batch:
        batch.add_column(sa.Column("approved_by",core.db.mixins.GUID()))
        batch.add_column(sa.Column("approved_at",sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("approval_notes",sa.Text()))
        batch.add_column(sa.Column("payment_status",sa.String(30),nullable=False,server_default="unpaid"))
        batch.add_column(sa.Column("amount_paid",sa.Numeric(14,2),nullable=False,server_default="0"))
        batch.add_column(sa.Column("payment_due_date",sa.String(10)))
        batch.add_column(sa.Column("rfq_id",core.db.mixins.GUID()))
        batch.create_foreign_key("fk_po_approved_by","users",["approved_by"],["id"])
        batch.create_foreign_key("fk_po_rfq","purchase_rfqs",["rfq_id"],["id"])
    op.create_index("ix_purchase_orders_payment_status","purchase_orders",["payment_status"])
    op.create_index("ix_purchase_orders_rfq_id","purchase_orders",["rfq_id"])
    with op.batch_alter_table("goods_receipts") as batch:
        batch.add_column(sa.Column("warehouse_id",core.db.mixins.GUID()))
        batch.add_column(sa.Column("receipt_number",sa.Text()))
        batch.add_column(sa.Column("quantity_returned",sa.Numeric(10,3),nullable=False,server_default="0"))
        batch.create_foreign_key("fk_receipt_warehouse","catalog_warehouses",["warehouse_id"],["id"])
    op.create_index("ix_goods_receipts_warehouse_id","goods_receipts",["warehouse_id"])
    op.create_table("purchase_returns",
        sa.Column("company_id",core.db.mixins.GUID(),nullable=False),sa.Column("supplier_id",core.db.mixins.GUID(),nullable=False),sa.Column("purchase_order_id",core.db.mixins.GUID(),nullable=False),
        sa.Column("return_number",sa.String(50),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("reason",sa.Text(),nullable=False),
        sa.Column("total_amount",sa.Numeric(14,2),nullable=False),sa.Column("created_by",core.db.mixins.GUID(),nullable=False),sa.Column("completed_by",core.db.mixins.GUID()),
        sa.Column("completed_at",sa.DateTime(timezone=True)),sa.Column("id",core.db.mixins.GUID(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["company_id"],["companies.id"]),sa.ForeignKeyConstraint(["supplier_id"],["suppliers.id"]),sa.ForeignKeyConstraint(["purchase_order_id"],["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["created_by"],["users.id"]),sa.ForeignKeyConstraint(["completed_by"],["users.id"]),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("company_id","return_number",name="uq_purchase_return_number"))
    for col in ("company_id","supplier_id","purchase_order_id","return_number","status"): op.create_index(f"ix_purchase_returns_{col}","purchase_returns",[col])
    op.create_table("purchase_return_lines",
        sa.Column("company_id",core.db.mixins.GUID(),nullable=False),sa.Column("purchase_return_id",core.db.mixins.GUID(),nullable=False),sa.Column("goods_receipt_id",core.db.mixins.GUID(),nullable=False),
        sa.Column("quantity",sa.Numeric(10,3),nullable=False),sa.Column("unit_cost",sa.Numeric(14,2),nullable=False),sa.Column("line_total",sa.Numeric(14,2),nullable=False),
        sa.Column("id",core.db.mixins.GUID(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["company_id"],["companies.id"]),sa.ForeignKeyConstraint(["purchase_return_id"],["purchase_returns.id"]),sa.ForeignKeyConstraint(["goods_receipt_id"],["goods_receipts.id"]),sa.PrimaryKeyConstraint("id"))
    for col in ("company_id","purchase_return_id","goods_receipt_id"): op.create_index(f"ix_purchase_return_lines_{col}","purchase_return_lines",[col])
    op.create_table("purchase_attachments",
        sa.Column("company_id",core.db.mixins.GUID(),nullable=False),sa.Column("entity_type",sa.String(30),nullable=False),sa.Column("entity_id",core.db.mixins.GUID(),nullable=False),
        sa.Column("document_id",core.db.mixins.GUID(),nullable=False),sa.Column("label",sa.String(200)),sa.Column("added_by",core.db.mixins.GUID(),nullable=False),
        sa.Column("id",core.db.mixins.GUID(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["company_id"],["companies.id"]),sa.ForeignKeyConstraint(["document_id"],["documents.id"]),sa.ForeignKeyConstraint(["added_by"],["users.id"]),sa.PrimaryKeyConstraint("id"))
    for col in ("company_id","entity_type","entity_id","document_id"): op.create_index(f"ix_purchase_attachments_{col}","purchase_attachments",[col])


def downgrade() -> None:
    op.drop_table("purchase_attachments"); op.drop_table("purchase_return_lines"); op.drop_table("purchase_returns")
    op.drop_index("ix_goods_receipts_warehouse_id",table_name="goods_receipts")
    with op.batch_alter_table("goods_receipts") as batch:
        batch.drop_constraint("fk_receipt_warehouse",type_="foreignkey"); batch.drop_column("quantity_returned"); batch.drop_column("receipt_number"); batch.drop_column("warehouse_id")
    op.drop_index("ix_purchase_orders_rfq_id",table_name="purchase_orders"); op.drop_index("ix_purchase_orders_payment_status",table_name="purchase_orders")
    with op.batch_alter_table("purchase_orders") as batch:
        batch.drop_constraint("fk_po_rfq",type_="foreignkey"); batch.drop_constraint("fk_po_approved_by",type_="foreignkey")
        for col in ("rfq_id","payment_due_date","amount_paid","payment_status","approval_notes","approved_at","approved_by"): batch.drop_column(col)
    op.drop_table("purchase_rfq_lines"); op.drop_table("purchase_rfqs"); op.drop_table("supplier_contacts")
    for col in ("rating","default_currency","payment_terms_days","tax_id"): op.drop_column("suppliers",col)
