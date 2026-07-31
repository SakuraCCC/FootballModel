"""Phase 11 quota, coverage, import and batch export persistence."""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0012"
down_revision = "20260731_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("raw_data_snapshots", sa.Column("request_hash", sa.String(64), nullable=True))
    op.add_column("raw_data_snapshots", sa.Column("cached", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("raw_data_snapshots", sa.Column("cache_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_raw_data_snapshots_request_hash", "raw_data_snapshots", ["request_hash"])

    for name, column in (
        ("plan_name", sa.String(120)),
        ("daily_limit", sa.Integer()),
        ("daily_remaining", sa.Integer()),
        ("minute_limit", sa.Integer()),
        ("minute_remaining", sa.Integer()),
        ("last_checked_at", sa.DateTime(timezone=True)),
        ("reset_at", sa.DateTime(timezone=True)),
        ("quota_state", sa.String(24)),
    ):
        op.add_column(
            "provider_quota_usage",
            sa.Column(
                name,
                column,
                nullable=name != "quota_state",
                server_default="unknown" if name == "quota_state" else None,
            ),
        )

    op.create_table(
        "competition_coverages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("competition_id", sa.String(36), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("season_id", sa.String(36), sa.ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("source_snapshot_id", sa.String(36), sa.ForeignKey("raw_data_snapshots.id", ondelete="SET NULL")),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("certainty", sa.String(24), nullable=False, server_default="reported"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("competition_id", "season_id", name="uq_competition_coverage_season"),
    )
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("import_batch_id", sa.String(36), unique=True, nullable=False),
        sa.Column("source_name", sa.String(160), nullable=False),
        sa.Column("source_url", sa.String(500)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("certainty", sa.String(24), nullable=False, server_default="reported"),
        sa.Column("imported_by", sa.String(80), nullable=False, server_default="admin"),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "batch_exports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("batch_id", name="uq_batch_exports_batch"),
    )


def downgrade() -> None:
    op.drop_table("batch_exports")
    op.drop_table("import_batches")
    op.drop_table("competition_coverages")
    for name in ("plan_name", "daily_limit", "daily_remaining", "minute_limit", "minute_remaining", "last_checked_at", "reset_at", "quota_state"):
        op.drop_column("provider_quota_usage", name)
    op.drop_index("ix_raw_data_snapshots_request_hash", table_name="raw_data_snapshots")
    op.drop_column("raw_data_snapshots", "cache_expires_at")
    op.drop_column("raw_data_snapshots", "cached")
    op.drop_column("raw_data_snapshots", "request_hash")
