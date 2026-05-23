"""actor profile tables

Revision ID: 0002
Revises: 0001_initial
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actor_profile_delta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field_name", sa.String(64), nullable=False, index=True),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="user_confirmed"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "actor_role_preference",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_category", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preference_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "actor_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("search_results.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(16), nullable=False, index=True),
        sa.Column("role_category", sa.String(64), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "profile_suggestion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("suggestion_type", sa.String(32), nullable=False),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column("search_results", sa.Column("role_category", sa.String(64), nullable=True))
    op.add_column("search_results", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("search_results", sa.Column("rationale", sa.Text(), nullable=True))
    op.add_column("search_results", sa.Column("red_flags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("search_results", "red_flags")
    op.drop_column("search_results", "rationale")
    op.drop_column("search_results", "deadline")
    op.drop_column("search_results", "role_category")
    op.drop_table("profile_suggestion")
    op.drop_table("actor_feedback")
    op.drop_table("actor_role_preference")
    op.drop_table("actor_profile_delta")
