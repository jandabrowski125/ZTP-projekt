"""Add event update metadata to user notifications.

Revision ID: 007_notification_event_updates
Revises: 006_custom_event_timezone
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007_notification_event_updates"
down_revision = "006_custom_event_timezone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_notifications", sa.Column("event_title", sa.String(300), nullable=True))
    op.add_column(
        "user_notifications",
        sa.Column("changed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_notifications", "changed_fields")
    op.drop_column("user_notifications", "event_title")
