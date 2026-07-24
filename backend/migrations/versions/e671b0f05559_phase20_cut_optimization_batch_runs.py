"""phase20_cut_optimization_batch_runs

Revision ID: e671b0f05559
Revises: 3abcf1e53be8
Create Date: 2026-07-24 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core.db.mixins


revision: str = 'e671b0f05559'
down_revision: Union[str, None] = '3abcf1e53be8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cut_optimization_batch_runs',
        sa.Column('company_id', core.db.mixins.GUID(), nullable=False),
        sa.Column('material_id', core.db.mixins.GUID(), nullable=True),
        sa.Column('kerf_mm', sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column('slabs', sa.JSON(), nullable=False),
        sa.Column('pieces', sa.JSON(), nullable=False),
        sa.Column('placements', sa.JSON(), nullable=False),
        sa.Column('unplaced', sa.JSON(), nullable=False),
        sa.Column('slabs_used_count', sa.Integer(), nullable=False),
        sa.Column('total_area_m2', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('placed_area_m2', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('waste_area_m2', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('utilization_pct', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', core.db.mixins.GUID(), nullable=True),
        sa.Column('id', core.db.mixins.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['material_id'], ['catalog_materials.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_cut_optimization_batch_runs_company_id'), 'cut_optimization_batch_runs', ['company_id'], unique=False
    )
    op.create_index(
        op.f('ix_cut_optimization_batch_runs_material_id'), 'cut_optimization_batch_runs', ['material_id'], unique=False
    )

    # Phase 18's RLS-continuity convention: a new tenant-owned (company_id)
    # table added after the original RLS migration gets its own policy
    # directly inside its own creation migration (see Phase 19's
    # production_notifications for the same pattern).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "cut_optimization_batch_runs" ENABLE ROW LEVEL SECURITY')
        op.execute(
            'CREATE POLICY company_isolation ON "cut_optimization_batch_runs" '
            "USING (company_id = current_setting('app.current_company_id', true)::uuid) "
            "WITH CHECK (company_id = current_setting('app.current_company_id', true)::uuid)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS company_isolation ON "cut_optimization_batch_runs"')
        op.execute('ALTER TABLE "cut_optimization_batch_runs" DISABLE ROW LEVEL SECURITY')

    op.drop_index(op.f('ix_cut_optimization_batch_runs_material_id'), table_name='cut_optimization_batch_runs')
    op.drop_index(op.f('ix_cut_optimization_batch_runs_company_id'), table_name='cut_optimization_batch_runs')
    op.drop_table('cut_optimization_batch_runs')
