"""Add enrolled list type support, event reminders, and notifications.

Revision ID: 005_enrolled_and_notifications
Revises: 004_custom_event_address
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_enrolled_and_notifications"
down_revision = "004_custom_event_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_event_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_event_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column(
            "custom_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("custom_events.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("event_title", sa.String(300), nullable=False),
        sa.Column("event_starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "public_event_id",
            "provider",
            "external_id",
            name="uq_user_event_reminder_aggregated",
        ),
        sa.UniqueConstraint("user_id", "custom_event_id", name="uq_user_event_reminder_custom"),
    )
    op.create_index("ix_user_event_reminders_user", "user_event_reminders", ["user_id"])

    op.create_table(
        "user_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("public_event_id", sa.Integer(), nullable=True),
        sa.Column("community_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_user_notifications_user_scheduled",
        "user_notifications",
        ["user_id", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_notifications_user_scheduled", table_name="user_notifications")
    op.drop_table("user_notifications")
    op.drop_index("ix_user_event_reminders_user", table_name="user_event_reminders")
    op.drop_table("user_event_reminders")
