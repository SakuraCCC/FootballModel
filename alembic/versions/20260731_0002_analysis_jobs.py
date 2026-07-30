"""Create analysis job pipeline tables.

Revision ID: 20260731_0002
Revises: 20260730_0001
Create Date: 2026-07-31 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0002"
down_revision = "20260730_0001"
branch_labels = None
depends_on = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), nullable=False),
        sa.Column("competition_name", sa.String(160), nullable=False),
        sa.Column("match_date", sa.Date(), nullable=False),
        sa.Column("model_version", sa.String(120), nullable=False),
        sa.Column("poster_style", sa.String(80), nullable=False),
        sa.Column("watermark", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("current_step", sa.String(64), nullable=False, server_default="created"),
        sa.Column("error_message", sa.Text(), nullable=True),
        *timestamp_columns(),
    )
    op.create_index("ix_analysis_jobs_batch_id", "analysis_jobs", ["batch_id"])
    op.create_table(
        "analysis_job_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("home_team", sa.String(160), nullable=False),
        sa.Column("away_team", sa.String(160), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("job_id", "home_team", "away_team", name="uq_analysis_job_matches_teams"),
    )
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "match_id",
            sa.String(36),
            sa.ForeignKey("analysis_job_matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("structured_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="completed"),
        *timestamp_columns(),
        sa.UniqueConstraint("job_id", "match_id", name="uq_analysis_results_job_match"),
    )


def downgrade() -> None:
    op.drop_table("analysis_results")
    op.drop_table("analysis_job_matches")
    op.drop_index("ix_analysis_jobs_batch_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
