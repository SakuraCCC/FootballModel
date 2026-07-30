"""Create prediction model version, run, and result tables.

Revision ID: 20260731_0004
Revises: 20260731_0003
Create Date: 2026-07-31 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0004"
down_revision = "20260731_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
    )
    op.create_table(
        "model_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_version_id", sa.String(36), sa.ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("input_snapshot_id", sa.String(36), sa.ForeignKey("raw_data_snapshots.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_model_runs_match_created", "model_runs", ["match_id", "created_at"])
    op.create_table(
        "prediction_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_run_id", sa.String(36), sa.ForeignKey("model_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("direction", sa.String(64), nullable=True),
        sa.Column("goal_range", sa.String(32), nullable=True),
        sa.Column("btts", sa.String(32), nullable=True),
        sa.Column("primary_score", sa.String(16), nullable=True),
        sa.Column("stable_score", sa.String(16), nullable=True),
        sa.Column("alternative_score", sa.String(16), nullable=True),
        sa.Column("review_summary", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("prediction_results")
    op.drop_index("ix_model_runs_match_created", table_name="model_runs")
    op.drop_table("model_runs")
    op.drop_table("model_versions")
