from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('searches', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('name', sa.String(120), nullable=False), sa.Column('interval_minutes', sa.Integer(), nullable=False), sa.Column('config', sa.JSON(), nullable=False), sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index('ix_searches_name', 'searches', ['name'], unique=True)
    op.create_table('search_runs', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('search_id', sa.Integer(), sa.ForeignKey('searches.id', ondelete='CASCADE'), nullable=False), sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('finished_at', sa.DateTime(timezone=True)), sa.Column('status', sa.String(32), nullable=False), sa.Column('error_message', sa.Text()))
    op.create_table('search_results', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('run_id', sa.Integer(), sa.ForeignKey('search_runs.id', ondelete='CASCADE'), nullable=False), sa.Column('title', sa.String(512), nullable=False), sa.Column('url', sa.String(2048), nullable=False), sa.Column('snippet', sa.Text(), nullable=False), sa.Column('content', sa.Text()), sa.Column('source', sa.String(50), nullable=False), sa.Column('published_at', sa.DateTime(timezone=True)), sa.Column('score', sa.Float()), sa.Column('summary', sa.Text()), sa.Column('content_hash', sa.String(64)), sa.UniqueConstraint('run_id', 'url', name='uq_run_url'))
    op.create_table('notifications', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('run_id', sa.Integer(), sa.ForeignKey('search_runs.id', ondelete='CASCADE'), nullable=False), sa.Column('channel', sa.String(50), nullable=False), sa.Column('payload', sa.JSON(), nullable=False), sa.Column('status', sa.String(20), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))

def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('search_results')
    op.drop_table('search_runs')
    op.drop_index('ix_searches_name', table_name='searches')
    op.drop_table('searches')
