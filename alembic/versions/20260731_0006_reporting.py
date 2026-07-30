"""Add generated report outputs.

Revision ID: 20260731_0006
Revises: 20260731_0005
Create Date: 2026-07-31 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0006"
down_revision = "20260731_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_outputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "prediction_id",
            sa.String(36),
            sa.ForeignKey("prediction_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("llm_model", sa.String(160), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_report_outputs_prediction_created", "report_outputs", ["prediction_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_report_outputs_prediction_created", table_name="report_outputs")
    op.drop_table("report_outputs")
