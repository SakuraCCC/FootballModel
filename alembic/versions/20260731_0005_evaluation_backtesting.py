"""Add result evaluation and model performance storage.

Revision ID: 20260731_0005
Revises: 20260731_0004
Create Date: 2026-07-31 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0005"
down_revision = "20260731_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("actual_results", sa.Column("result", sa.String(16), nullable=True))
    op.add_column("actual_results", sa.Column("total_goals", sa.Integer(), nullable=True))
    op.add_column("actual_results", sa.Column("btts_result", sa.Boolean(), nullable=True))
    op.add_column("actual_results", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "model_runs",
        sa.Column(
            "prediction_id",
            sa.String(36),
            sa.ForeignKey("prediction_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_model_runs_prediction_id", "model_runs", ["prediction_id"])
    op.create_table(
        "prediction_evaluations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "prediction_id",
            sa.String(36),
            sa.ForeignKey("prediction_results.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "actual_result_id",
            sa.String(36),
            sa.ForeignKey("actual_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("direction_correct", sa.Boolean(), nullable=False),
        sa.Column("score_exact_correct", sa.Boolean(), nullable=False),
        sa.Column("score_top3_correct", sa.Boolean(), nullable=False),
        sa.Column("goal_range_correct", sa.Boolean(), nullable=False),
        sa.Column("btts_correct", sa.Boolean(), nullable=False),
        sa.Column("log_loss", sa.Float(), nullable=True),
        sa.Column("brier_score", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "model_performance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "competition_id",
            sa.String(36),
            sa.ForeignKey("competitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("log_loss", sa.Float(), nullable=True),
        sa.Column("brier_score", sa.Float(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "model_version_id",
            "competition_id",
            name="uq_model_performance_version_competition",
        ),
    )


def downgrade() -> None:
    op.drop_table("model_performance")
    op.drop_table("prediction_evaluations")
    op.drop_index("ix_model_runs_prediction_id", table_name="model_runs")
    op.drop_column("model_runs", "prediction_id")
    op.drop_column("actual_results", "completed_at")
    op.drop_column("actual_results", "btts_result")
    op.drop_column("actual_results", "total_goals")
    op.drop_column("actual_results", "result")
