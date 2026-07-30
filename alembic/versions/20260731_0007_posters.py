"""Add poster generation and publishing records.

Revision ID: 20260731_0007
Revises: 20260731_0006
Create Date: 2026-07-31 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0007"
down_revision = "20260731_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "poster_outputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "report_id", sa.String(36), sa.ForeignKey("report_outputs.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "prediction_id",
            sa.String(36),
            sa.ForeignKey("prediction_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("competition_style", sa.String(32), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("template_version", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_poster_outputs_report_created", "poster_outputs", ["report_id", "created_at"])
    op.create_table(
        "content_publish_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "report_id", sa.String(36), sa.ForeignKey("report_outputs.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "poster_id", sa.String(36), sa.ForeignKey("poster_outputs.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("publish_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("collects", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("content_publish_records")
    op.drop_index("ix_poster_outputs_report_created", table_name="poster_outputs")
    op.drop_table("poster_outputs")
