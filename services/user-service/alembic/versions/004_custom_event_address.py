"""Add address_line and postal_code to custom_events.

Revision ID: 004_custom_event_address
Revises: 003_user_firebase_uid
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = "004_custom_event_address"
down_revision = "003_user_firebase_uid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "custom_events",
        sa.Column("address_line", sa.String(300), nullable=True),
    )
    op.add_column(
        "custom_events",
        sa.Column("postal_code", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("custom_events", "postal_code")
    op.drop_column("custom_events", "address_line")
