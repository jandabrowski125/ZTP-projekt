"""Widen users.avatar_url to TEXT for base64 profile photos.

Revision ID: 008_user_avatar_text
Revises: 007_notification_event_updates
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "008_user_avatar_text"
down_revision = "007_notification_event_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "avatar_url",
        existing_type=sa.String(2048),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "avatar_url",
        existing_type=sa.Text(),
        type_=sa.String(2048),
        existing_nullable=True,
    )
