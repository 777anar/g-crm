"""phase19_production_notifications

Revision ID: 3abcf1e53be8
Revises: 55d19b5b6862
Create Date: 2026-07-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core.db.mixins


revision: str = '3abcf1e53be8'
down_revision: Union[str, None] = '55d19b5b6862'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'production_notifications',
        sa.Column('company_id', core.db.mixins.GUID(), nullable=False),
        sa.Column('user_id', core.db.mixins.GUID(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('work_order_id', core.db.mixins.GUID(), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', core.db.mixins.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_production_notifications_company_id'), 'production_notifications', ['company_id'], unique=False
    )
    op.create_index(
        op.f('ix_production_notifications_user_id'), 'production_notifications', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_production_notifications_work_order_id'),
        'production_notifications',
        ['work_order_id'],
        unique=False,
    )

    # Phase 19's RLS-continuity: production_notifications is a new
    # tenant-owned (company_id) table added after Phase 18's RLS migration
    # already ran, so it needs its own policy rather than waiting for a
    # future full RLS pass to notice it's missing one.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "production_notifications" ENABLE ROW LEVEL SECURITY')
        op.execute(
            'CREATE POLICY company_isolation ON "production_notifications" '
            "USING (company_id = current_setting('app.current_company_id', true)::uuid) "
            "WITH CHECK (company_id = current_setting('app.current_company_id', true)::uuid)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS company_isolation ON "production_notifications"')
        op.execute('ALTER TABLE "production_notifications" DISABLE ROW LEVEL SECURITY')

    op.drop_index(op.f('ix_production_notifications_work_order_id'), table_name='production_notifications')
    op.drop_index(op.f('ix_production_notifications_user_id'), table_name='production_notifications')
    op.drop_index(op.f('ix_production_notifications_company_id'), table_name='production_notifications')
    op.drop_table('production_notifications')
