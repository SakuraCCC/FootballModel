"""Add Phase 10 real ingestion and review workflow.

Revision ID: 20260731_0010
Revises: 20260731_0009
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0010"
down_revision = "20260731_0009"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.add_column("report_outputs", sa.Column("review_status", sa.String(24), nullable=False, server_default="draft"))
    op.add_column("report_outputs", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("report_outputs", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column("poster_outputs", sa.Column("review_status", sa.String(24), nullable=False, server_default="draft"))
    op.add_column("poster_outputs", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("poster_outputs", sa.Column("review_notes", sa.Text(), nullable=True))
    op.create_table("competition_standings", sa.Column("id", sa.String(36), primary_key=True), sa.Column("competition_id", sa.String(36), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False), sa.Column("season_id", sa.String(36), sa.ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=False), sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False), sa.Column("rank", sa.Integer()), sa.Column("points", sa.Integer()), sa.Column("goals_for", sa.Integer()), sa.Column("goals_against", sa.Integer()), sa.Column("goal_difference", sa.Integer()), sa.Column("form", sa.String(32)), sa.Column("source_snapshot_id", sa.String(36), sa.ForeignKey("raw_data_snapshots.id", ondelete="SET NULL")), sa.Column("certainty", sa.String(24), nullable=False, server_default="reported"), *_timestamps(), sa.UniqueConstraint("competition_id", "season_id", "team_id", name="uq_competition_standings_team"))
    op.create_table("player_season_stats", sa.Column("id", sa.String(36), primary_key=True), sa.Column("player_id", sa.String(36), sa.ForeignKey("players.id", ondelete="RESTRICT"), nullable=False), sa.Column("season_id", sa.String(36), sa.ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=False), sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="SET NULL")), sa.Column("position", sa.String(32)), sa.Column("minutes_played", sa.Integer()), sa.Column("appearances", sa.Integer()), sa.Column("goals", sa.Integer()), sa.Column("assists", sa.Integer()), sa.Column("source_snapshot_id", sa.String(36), sa.ForeignKey("raw_data_snapshots.id", ondelete="SET NULL")), sa.Column("certainty", sa.String(24), nullable=False, server_default="reported"), *_timestamps(), sa.UniqueConstraint("player_id", "season_id", name="uq_player_season_stats_player"))
    op.create_table("injuries", sa.Column("id", sa.String(36), primary_key=True), sa.Column("external_id", sa.String(120)), sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="SET NULL")), sa.Column("player_id", sa.String(36), sa.ForeignKey("players.id", ondelete="SET NULL")), sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="SET NULL")), sa.Column("status", sa.String(80)), sa.Column("reason", sa.String(255)), sa.Column("injury_type", sa.String(80)), sa.Column("source_snapshot_id", sa.String(36), sa.ForeignKey("raw_data_snapshots.id", ondelete="SET NULL")), sa.Column("certainty", sa.String(24), nullable=False, server_default="reported"), *_timestamps(), sa.UniqueConstraint("external_id", "match_id", "player_id", name="uq_injuries_source_record"))
    op.create_table("match_lineups", sa.Column("id", sa.String(36), primary_key=True), sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False), sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False), sa.Column("player_id", sa.String(36), sa.ForeignKey("players.id", ondelete="SET NULL")), sa.Column("external_player_id", sa.String(80)), sa.Column("player_name", sa.String(160)), sa.Column("starter", sa.Boolean()), sa.Column("position", sa.String(32)), sa.Column("jersey", sa.Integer()), sa.Column("source_snapshot_id", sa.String(36), sa.ForeignKey("raw_data_snapshots.id", ondelete="SET NULL")), sa.Column("certainty", sa.String(24), nullable=False, server_default="reported"), *_timestamps(), sa.UniqueConstraint("match_id", "team_id", "external_player_id", name="uq_match_lineups_player"))
    op.create_table("provider_quota_usage", sa.Column("id", sa.String(36), primary_key=True), sa.Column("source_id", sa.String(36), sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False), sa.Column("usage_date", sa.Date(), nullable=False), sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("quota_limit", sa.Integer()), sa.Column("remaining", sa.Integer()), sa.Column("last_status", sa.Integer()), sa.Column("last_retrieved_at", sa.DateTime(timezone=True)), *_timestamps(), sa.UniqueConstraint("source_id", "usage_date", name="uq_provider_quota_usage_day"))


def downgrade() -> None:
    op.drop_table("provider_quota_usage")
    op.drop_table("match_lineups")
    op.drop_table("injuries")
    op.drop_table("player_season_stats")
    op.drop_table("competition_standings")
    for table in ("poster_outputs", "report_outputs"):
        op.drop_column(table, "review_notes")
        op.drop_column(table, "reviewed_at")
        op.drop_column(table, "review_status")
