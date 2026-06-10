"""Add event_timezone to custom_events.

Revision ID: 006_custom_event_timezone
Revises: 005_enrolled_and_notifications
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "006_custom_event_timezone"
down_revision = "005_enrolled_and_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("custom_events", sa.Column("event_timezone", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("custom_events", "event_timezone")
