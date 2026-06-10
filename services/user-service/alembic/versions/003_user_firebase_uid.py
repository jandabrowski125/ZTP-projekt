"""Add firebase_uid to users for Firebase Auth linking.

Revision ID: 003_user_firebase_uid
Revises: 002_custom_event_image_text
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "003_user_firebase_uid"
down_revision = "002_custom_event_image_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("firebase_uid", sa.String(128), nullable=True))
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_column("users", "firebase_uid")
