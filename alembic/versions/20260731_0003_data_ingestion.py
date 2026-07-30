"""Add provider ingestion, source tracking, and normalized entity fields.

Revision ID: 20260731_0003
Revises: 20260731_0002
Create Date: 2026-07-31 00:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0003"
down_revision = "20260731_0002"
branch_labels = None
depends_on = None

CERTAINTY_VALUES = "'official', 'confirmed', 'reported', 'predicted', 'unavailable'"


def upgrade() -> None:
    op.add_column("competitions", sa.Column("api_football_league_id", sa.Integer(), nullable=True))
    op.add_column("competitions", sa.Column("provider_name", sa.String(160), nullable=True))
    op.add_column(
        "competitions",
        sa.Column("certainty", sa.String(24), nullable=False, server_default="unavailable"),
    )
    op.create_check_constraint(
        "ck_competitions_certainty", "competitions", f"certainty IN ({CERTAINTY_VALUES})"
    )

    op.add_column("data_sources", sa.Column("source_name", sa.String(120), nullable=True))
    op.add_column(
        "data_sources",
        sa.Column("source_tier", sa.String(32), nullable=False, server_default="secondary"),
    )
    op.add_column("data_sources", sa.Column("api_version", sa.String(32), nullable=True))
    op.execute("UPDATE data_sources SET source_name = name WHERE source_name IS NULL")
    op.alter_column("data_sources", "source_name", nullable=False)

    op.add_column(
        "seasons",
        sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True),
    )
    op.add_column("seasons", sa.Column("certainty", sa.String(24), nullable=False, server_default="unavailable"))
    op.create_check_constraint("ck_seasons_certainty", "seasons", f"certainty IN ({CERTAINTY_VALUES})")

    op.add_column("teams", sa.Column("normalized_name", sa.String(160), nullable=True))
    op.add_column("teams", sa.Column("external_id", sa.String(80), nullable=True))
    op.add_column(
        "teams",
        sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True),
    )
    op.add_column("teams", sa.Column("certainty", sa.String(24), nullable=False, server_default="unavailable"))
    op.create_index("ix_teams_normalized_name", "teams", ["normalized_name"])
    op.create_index("ix_teams_source_external", "teams", ["source_id", "external_id"], unique=True)
    op.create_check_constraint("ck_teams_certainty", "teams", f"certainty IN ({CERTAINTY_VALUES})")

    op.alter_column("matches", "home_team_id", existing_type=sa.String(36), nullable=True)
    op.alter_column("matches", "away_team_id", existing_type=sa.String(36), nullable=True)
    op.alter_column("matches", "kickoff_at", existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column("matches", "status", existing_type=sa.String(24), nullable=True)
    op.add_column("matches", sa.Column("external_id", sa.String(80), nullable=True))
    op.add_column(
        "matches",
        sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True),
    )
    op.add_column("matches", sa.Column("certainty", sa.String(24), nullable=False, server_default="unavailable"))
    op.create_index("ix_matches_source_external", "matches", ["source_id", "external_id"], unique=True)
    op.create_check_constraint("ck_matches_certainty", "matches", f"certainty IN ({CERTAINTY_VALUES})")

    op.create_table(
        "players",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_name", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(160), nullable=False),
        sa.Column("external_id", sa.String(80), nullable=True),
        sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("certainty", sa.String(24), nullable=False, server_default="unavailable"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(f"certainty IN ({CERTAINTY_VALUES})", name="ck_players_certainty"),
    )
    op.create_index("ix_players_normalized_name", "players", ["normalized_name"])
    op.create_index("ix_players_source_external", "players", ["source_id", "external_id"], unique=True)

    op.create_table(
        "raw_data_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "data_source_id",
            sa.String(36),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(120), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_raw_data_snapshots_source_retrieved",
        "raw_data_snapshots",
        ["data_source_id", "retrieved_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_data_snapshots_source_retrieved", table_name="raw_data_snapshots")
    op.drop_table("raw_data_snapshots")
    op.drop_index("ix_players_source_external", table_name="players")
    op.drop_index("ix_players_normalized_name", table_name="players")
    op.drop_table("players")
    op.drop_constraint("ck_matches_certainty", "matches", type_="check")
    op.drop_index("ix_matches_source_external", table_name="matches")
    op.drop_column("matches", "certainty")
    op.drop_column("matches", "source_id")
    op.drop_column("matches", "external_id")
    op.alter_column("matches", "status", existing_type=sa.String(24), nullable=False)
    op.alter_column("matches", "kickoff_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column("matches", "away_team_id", existing_type=sa.String(36), nullable=False)
    op.alter_column("matches", "home_team_id", existing_type=sa.String(36), nullable=False)
    op.drop_constraint("ck_teams_certainty", "teams", type_="check")
    op.drop_index("ix_teams_source_external", table_name="teams")
    op.drop_index("ix_teams_normalized_name", table_name="teams")
    op.drop_column("teams", "certainty")
    op.drop_column("teams", "source_id")
    op.drop_column("teams", "external_id")
    op.drop_column("teams", "normalized_name")
    op.drop_constraint("ck_seasons_certainty", "seasons", type_="check")
    op.drop_column("seasons", "certainty")
    op.drop_column("seasons", "source_id")
    op.drop_column("data_sources", "api_version")
    op.drop_column("data_sources", "source_tier")
    op.drop_column("data_sources", "source_name")
    op.drop_constraint("ck_competitions_certainty", "competitions", type_="check")
    op.drop_column("competitions", "certainty")
    op.drop_column("competitions", "provider_name")
    op.drop_column("competitions", "api_football_league_id")
