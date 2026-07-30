"""Create Phase 1 schema and supported competition metadata.

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260730_0001"
down_revision = None
branch_labels = None
depends_on = None

COMPETITIONS = [
    ("b0000000-0000-4000-8000-000000000001", "CSL", "Chinese Super League", "China"),
    ("b0000000-0000-4000-8000-000000000002", "MLS", "Major League Soccer", "United States and Canada"),
    ("b0000000-0000-4000-8000-000000000003", "LIGA_MX", "Liga MX", "Mexico"),
    ("b0000000-0000-4000-8000-000000000004", "UCL_QUALIFIER", "UEFA Champions League Qualifying", "Europe"),
    ("b0000000-0000-4000-8000-000000000005", "BRA_SERIE_A", "Campeonato Brasileiro Serie A", "Brazil"),
]


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "competitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("region", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamp_columns(),
    )
    op.create_table(
        "seasons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("competition_id", sa.String(36), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        *timestamp_columns(),
        sa.UniqueConstraint("competition_id", "code", name="uq_seasons_competition_code"),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_name", sa.String(160), nullable=False),
        sa.Column("country_code", sa.String(8), nullable=True),
        *timestamp_columns(),
        sa.UniqueConstraint("canonical_name", "country_code", name="uq_teams_name_country"),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("competition_id", sa.String(36), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("season_id", sa.String(36), sa.ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("home_team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("away_team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="scheduled"),
        *timestamp_columns(),
        sa.CheckConstraint("home_team_id <> away_team_id", name="ck_matches_distinct_teams"),
    )
    op.create_index("ix_matches_competition_kickoff", "matches", ["competition_id", "kickoff_at"])
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("reliability_level", sa.String(24), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamp_columns(),
    )
    op.create_table(
        "predictions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("data_snapshot_ref", sa.String(255), nullable=False),
        sa.Column("output_version", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        *timestamp_columns(),
    )
    op.create_index("ix_predictions_match_created", "predictions", ["match_id", "created_at"])
    op.create_table(
        "actual_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("result_source_id", sa.String(36), sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamp_columns(),
    )
    competitions = sa.table(
        "competitions", sa.column("id", sa.String), sa.column("code", sa.String), sa.column("name", sa.String), sa.column("region", sa.String)
    )
    op.bulk_insert(competitions, [dict(zip(("id", "code", "name", "region"), row, strict=True)) for row in COMPETITIONS])


def downgrade() -> None:
    op.drop_table("actual_results")
    op.drop_index("ix_predictions_match_created", table_name="predictions")
    op.drop_table("predictions")
    op.drop_table("data_sources")
    op.drop_index("ix_matches_competition_kickoff", table_name="matches")
    op.drop_table("matches")
    op.drop_table("teams")
    op.drop_table("seasons")
    op.drop_table("competitions")
