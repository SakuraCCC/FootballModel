"""Track unpublished and provider-reported lineup state.

Revision ID: 20260731_0011
Revises: 20260731_0010
"""

import sqlalchemy as sa

from alembic import op

revision = "20260731_0011"
down_revision = "20260731_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("lineup_status", sa.String(24), nullable=False, server_default="unavailable"))


def downgrade() -> None:
    op.drop_column("matches", "lineup_status")
