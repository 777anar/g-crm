"""phase21_ai_provider_call_logs

Revision ID: e12a7189e238
Revises: e671b0f05559
Create Date: 2026-07-24 10:52:25.001095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core.db.mixins


revision: str = 'e12a7189e238'
down_revision: Union[str, None] = 'e671b0f05559'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_provider_call_logs',
        sa.Column('company_id', core.db.mixins.GUID(), nullable=False),
        sa.Column('requested_by', core.db.mixins.GUID(), nullable=True),
        sa.Column('analysis_kind', sa.String(length=20), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('id', core.db.mixins.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_provider_call_logs_analysis_kind'), 'ai_provider_call_logs', ['analysis_kind'], unique=False)
    op.create_index(op.f('ix_ai_provider_call_logs_company_id'), 'ai_provider_call_logs', ['company_id'], unique=False)
    op.create_index(op.f('ix_ai_provider_call_logs_provider'), 'ai_provider_call_logs', ['provider'], unique=False)

    # batch_alter_table: SQLite has no ALTER-TABLE-ADD-CONSTRAINT support, so
    # adding a column with a new FK requires Alembic's copy-and-move batch
    # strategy there; on Postgres this still emits plain ALTER TABLE.
    with op.batch_alter_table('ai_recommendations') as batch_op:
        batch_op.add_column(sa.Column('provider_call_id', core.db.mixins.GUID(), nullable=True))
        batch_op.create_foreign_key(
            'fk_ai_recommendations_provider_call_id_ai_provider_call_logs',
            'ai_provider_call_logs', ['provider_call_id'], ['id'],
        )

    # Phase 18's RLS-continuity convention: a new tenant-owned (company_id)
    # table added after the original RLS migration gets its own policy
    # directly inside its own creation migration (see Phase 19's
    # production_notifications / Phase 20's cut_optimization_batch_runs for
    # the same pattern).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "ai_provider_call_logs" ENABLE ROW LEVEL SECURITY')
        op.execute(
            'CREATE POLICY company_isolation ON "ai_provider_call_logs" '
            "USING (company_id = current_setting('app.current_company_id', true)::uuid) "
            "WITH CHECK (company_id = current_setting('app.current_company_id', true)::uuid)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('DROP POLICY IF EXISTS company_isolation ON "ai_provider_call_logs"')
        op.execute('ALTER TABLE "ai_provider_call_logs" DISABLE ROW LEVEL SECURITY')

    with op.batch_alter_table('ai_recommendations') as batch_op:
        batch_op.drop_constraint('fk_ai_recommendations_provider_call_id_ai_provider_call_logs', type_='foreignkey')
        batch_op.drop_column('provider_call_id')
    op.drop_index(op.f('ix_ai_provider_call_logs_provider'), table_name='ai_provider_call_logs')
    op.drop_index(op.f('ix_ai_provider_call_logs_company_id'), table_name='ai_provider_call_logs')
    op.drop_index(op.f('ix_ai_provider_call_logs_analysis_kind'), table_name='ai_provider_call_logs')
    op.drop_table('ai_provider_call_logs')
