"""Initial users, saved events, custom events schema.

Revision ID: 001
Revises:
Create Date: 2026-06-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("avatar_url", sa.String(2048), nullable=True),
        sa.Column("preferences", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "custom_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("short_title", sa.String(80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("venue", sa.String(300), nullable=False),
        sa.Column("location", sa.String(300), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("category_color", sa.String(16), server_default="#7c3aed", nullable=False),
        sa.Column("price_label", sa.String(64), nullable=True),
        sa.Column("image_url", sa.String(2048), nullable=True),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("lineup", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("tickets", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_custom_events_owner_user_id", "custom_events", ["owner_user_id"])

    op.create_table(
        "user_saved_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("list_type", sa.String(20), nullable=False),
        sa.Column("public_event_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("custom_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("custom_events.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("attended_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "list_type", "public_event_id", "provider", "external_id", name="uq_user_saved_aggregated"),
        sa.UniqueConstraint("user_id", "list_type", "custom_event_id", name="uq_user_saved_custom"),
    )
    op.create_index("ix_user_saved_events_user_list", "user_saved_events", ["user_id", "list_type"])


def downgrade() -> None:
    op.drop_index("ix_user_saved_events_user_list", table_name="user_saved_events")
    op.drop_table("user_saved_events")
    op.drop_index("ix_custom_events_owner_user_id", table_name="custom_events")
    op.drop_table("custom_events")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
