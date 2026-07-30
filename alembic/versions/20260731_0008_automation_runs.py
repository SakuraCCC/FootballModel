"""Add automation run audit storage.

Revision ID: 20260731_0008
Revises: 20260731_0007
Create Date: 2026-07-31 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0008"
down_revision = "20260731_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("analysis_job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prediction_id", sa.String(36), sa.ForeignKey("prediction_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("report_outputs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("poster_id", sa.String(36), sa.ForeignKey("poster_outputs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_step", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("task_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_automation_runs_status_created", "automation_runs", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_automation_runs_status_created", table_name="automation_runs")
    op.drop_table("automation_runs")
