"""phase18_mfa_and_audit_retention

Revision ID: f39076f4e8fa
Revises: 98b251470b25
Create Date: 2026-07-23 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core.db.mixins


revision: str = 'f39076f4e8fa'
down_revision: Union[str, None] = '98b251470b25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `server_default` here only backfills existing rows at migration time;
    # left in place afterward rather than dropped via a follow-up
    # ALTER COLUMN (SQLite -- the test/dev database -- can't ALTER a column's
    # default in place), which is harmless since it matches the SQLAlchemy
    # model's own Python-side default.
    op.add_column('users', sa.Column('mfa_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column('companies', sa.Column('mfa_required_roles', sa.JSON(), nullable=False, server_default='[]'))

    op.create_table(
        'audit_retention_policies',
        sa.Column('company_id', core.db.mixins.GUID(), nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=True),
        sa.Column('updated_by', core.db.mixins.GUID(), nullable=False),
        sa.Column('id', core.db.mixins.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id'),
    )
    op.create_index(
        op.f('ix_audit_retention_policies_company_id'), 'audit_retention_policies', ['company_id'], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_retention_policies_company_id'), table_name='audit_retention_policies')
    op.drop_table('audit_retention_policies')
    op.drop_column('companies', 'mfa_required_roles')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'mfa_secret')
