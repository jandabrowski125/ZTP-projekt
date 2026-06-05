"""Widen custom_events.image_url to TEXT for base64 cover images.

Revision ID: 002_custom_event_image_text
Revises: 001_initial_schema
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "002_custom_event_image_text"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "custom_events",
        "image_url",
        existing_type=sa.String(2048),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "custom_events",
        "image_url",
        existing_type=sa.Text(),
        type_=sa.String(2048),
        existing_nullable=True,
    )
