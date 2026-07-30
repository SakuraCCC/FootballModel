"""Add Phase 9 hardening, calibration, statistics, and archive storage.

Revision ID: 20260731_0009
Revises: 20260731_0008
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0009"
down_revision = "20260731_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("automation_runs", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column("automation_runs", sa.Column("failed_step", sa.String(64), nullable=True))
    op.add_column("automation_runs", sa.Column("last_retry_time", sa.DateTime(timezone=True), nullable=True))
    for field in ("feature_version", "data_version", "prompt_version", "calibration_version"):
        op.add_column("model_versions", sa.Column(field, sa.String(80), nullable=True))
        op.add_column("model_runs", sa.Column(field, sa.String(120) if field == "data_version" else sa.String(80), nullable=True))
    op.create_table("match_statistics", sa.Column("id", sa.String(36), primary_key=True), sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False), sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False), sa.Column("shots", sa.Integer()), sa.Column("shots_on_target", sa.Integer()), sa.Column("possession", sa.Float()), sa.Column("corners", sa.Integer()), sa.Column("xg", sa.Float()), sa.Column("xga", sa.Float()), sa.Column("certainty", sa.String(24), nullable=False, server_default="unavailable"), sa.Column("source_snapshot_id", sa.String(36), sa.ForeignKey("raw_data_snapshots.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("match_id", "team_id", name="uq_match_statistics_match_team"))
    op.create_table("player_importance_scores", sa.Column("id", sa.String(36), primary_key=True), sa.Column("player_id", sa.String(36), sa.ForeignKey("players.id", ondelete="RESTRICT"), nullable=False), sa.Column("minutes_played", sa.Integer()), sa.Column("goals", sa.Integer()), sa.Column("assists", sa.Integer()), sa.Column("position", sa.String(32)), sa.Column("position_weight", sa.Float()), sa.Column("score", sa.Float()), sa.Column("certainty", sa.String(24), nullable=False, server_default="unavailable"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("player_id", name="uq_player_importance_scores_player"))
    op.create_table("scheduler_heartbeats", sa.Column("id", sa.String(36), primary_key=True), sa.Column("task_name", sa.String(120), nullable=False), sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("task_id", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("task_name", name="uq_scheduler_heartbeats_task_name"))
    op.create_table("confidence_calibration", sa.Column("id", sa.String(36), primary_key=True), sa.Column("model_version_id", sa.String(36), sa.ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False), sa.Column("competition_id", sa.String(36), sa.ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False), sa.Column("probability_bin", sa.String(16), nullable=False), sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("observed_frequency", sa.Float()), sa.Column("calibration_error", sa.Float()), sa.Column("reliability", sa.Float()), sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("model_version_id", "competition_id", "probability_bin", name="uq_confidence_calibration_bin"))
    op.create_table("prediction_archive", sa.Column("id", sa.String(36), primary_key=True), sa.Column("prediction_id", sa.String(36), sa.ForeignKey("prediction_results.id", ondelete="RESTRICT"), nullable=False, unique=True), sa.Column("input_summary", sa.JSON(), nullable=False), sa.Column("model_output", sa.JSON(), nullable=False), sa.Column("report_content", sa.Text()), sa.Column("poster_path", sa.String(500)), sa.Column("actual_result", sa.JSON()), sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("prediction_archive")
    op.drop_table("confidence_calibration")
    op.drop_table("scheduler_heartbeats")
    op.drop_table("player_importance_scores")
    op.drop_table("match_statistics")
    for field in ("calibration_version", "prompt_version", "data_version", "feature_version"):
        op.drop_column("model_runs", field)
        op.drop_column("model_versions", field)
    op.drop_column("automation_runs", "last_retry_time")
    op.drop_column("automation_runs", "failed_step")
    op.drop_column("automation_runs", "failure_reason")
