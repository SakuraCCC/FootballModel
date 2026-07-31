"""V3.2 release metadata and daily operations."""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0013"
down_revision = "20260731_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, columns in {
        "prediction_results": (
            ("model_version", sa.String(120)),
            ("feature_version", sa.String(80)),
            ("data_version", sa.String(120)),
            ("prompt_version", sa.String(80)),
            ("poster_version", sa.String(80)),
        ),
        "report_outputs": (
            ("model_version", sa.String(120)),
            ("feature_version", sa.String(80)),
            ("data_version", sa.String(120)),
            ("poster_version", sa.String(80)),
        ),
        "poster_outputs": (
            ("model_version", sa.String(120)),
            ("feature_version", sa.String(80)),
            ("data_version", sa.String(120)),
            ("prompt_version", sa.String(80)),
            ("poster_version", sa.String(80)),
        ),
        "prediction_archive": (
            ("model_version", sa.String(120)),
            ("feature_version", sa.String(80)),
            ("data_version", sa.String(120)),
            ("prompt_version", sa.String(80)),
            ("poster_version", sa.String(80)),
        ),
    }.items():
        for name, column_type in columns:
            op.add_column(table, sa.Column(name, column_type, nullable=True))

    op.create_table(
        "prompt_experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prompt_name", sa.String(120), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("change_description", sa.Text(), nullable=False),
        sa.Column("related_reports", sa.JSON(), nullable=False),
        sa.Column("performance_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "daily_operation_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("analysis_match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_state", sa.String(24), nullable=False, server_default="unknown"),
        sa.Column("report_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("poster_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("report_date", name="uq_daily_operation_reports_date"),
    )


def downgrade() -> None:
    op.drop_table("daily_operation_reports")
    op.drop_table("prompt_experiments")
    for table, columns in {
        "prediction_results": ("model_version", "feature_version", "data_version", "prompt_version", "poster_version"),
        "report_outputs": ("model_version", "feature_version", "data_version", "poster_version"),
        "poster_outputs": ("model_version", "feature_version", "data_version", "prompt_version", "poster_version"),
        "prediction_archive": ("model_version", "feature_version", "data_version", "prompt_version", "poster_version"),
    }.items():
        for name in columns:
            op.drop_column(table, name)

