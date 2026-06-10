import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from user_app.db.base import Base


class CustomEventStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class SavedEventListType(str, enum.Enum):
    FAVORITE = "favorite"
    ENROLLED = "enrolled"
    PAST = "past"


class NotificationType(str, enum.Enum):
    EVENT_REMINDER = "event_reminder"
    EVENT_UPDATED = "event_updated"
    SYSTEM = "system"


class User(Base):
    """Login credentials and personal profile (single table)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    saved_events: Mapped[list["UserSavedEvent"]] = relationship(back_populates="user")
    custom_events: Mapped[list["CustomEvent"]] = relationship(back_populates="owner")
    notifications: Mapped[list["UserNotification"]] = relationship(back_populates="user")
    event_reminders: Mapped[list["UserEventReminder"]] = relationship(back_populates="user")


class UserSavedEvent(Base):
    """Favorites and attended (past) events for a user."""

    __tablename__ = "user_saved_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "list_type",
            "public_event_id",
            "provider",
            "external_id",
            name="uq_user_saved_aggregated",
        ),
        UniqueConstraint(
            "user_id",
            "list_type",
            "custom_event_id",
            name="uq_user_saved_custom",
        ),
        Index("ix_user_saved_events_user_list", "user_id", "list_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    list_type: Mapped[SavedEventListType] = mapped_column(
        Enum(SavedEventListType, name="saved_event_list_type", native_enum=False),
        nullable=False,
    )
    public_event_id: Mapped[int | None] = mapped_column(nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    custom_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custom_events.id", ondelete="CASCADE"), nullable=True
    )
    event_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    attended_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="saved_events")
    custom_event: Mapped["CustomEvent | None"] = relationship(back_populates="saved_links")


class CustomEvent(Base):
    """User/venue-created events (future in-app publishing)."""

    __tablename__ = "custom_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    short_title: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue: Mapped[str] = mapped_column(String(300), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    address_line: Mapped[str | None] = mapped_column(String(300), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    category_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#7c3aed")
    price_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[CustomEventStatus] = mapped_column(
        Enum(CustomEventStatus, name="custom_event_status", native_enum=False),
        nullable=False,
        default=CustomEventStatus.DRAFT,
    )
    lineup: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    tickets: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="custom_events")
    saved_links: Mapped[list["UserSavedEvent"]] = relationship(back_populates="custom_event")


class UserEventReminder(Base):
    """Tracks per-event reminder subscriptions (24h / 6h / 1h before start)."""

    __tablename__ = "user_event_reminders"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "public_event_id",
            "provider",
            "external_id",
            name="uq_user_event_reminder_aggregated",
        ),
        UniqueConstraint("user_id", "custom_event_id", name="uq_user_event_reminder_custom"),
        Index("ix_user_event_reminders_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    public_event_id: Mapped[int] = mapped_column(nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    custom_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custom_events.id", ondelete="CASCADE"), nullable=True
    )
    event_title: Mapped[str] = mapped_column(String(300), nullable=False)
    event_starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="event_reminders")


class UserNotification(Base):
    """In-app notifications (event reminders and system messages)."""

    __tablename__ = "user_notifications"
    __table_args__ = (Index("ix_user_notifications_user_scheduled", "user_id", "scheduled_for"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", native_enum=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    public_event_id: Mapped[int | None] = mapped_column(nullable=True)
    community_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    changed_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="notifications")
