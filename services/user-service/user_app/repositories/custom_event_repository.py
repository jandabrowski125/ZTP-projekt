import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from eventradar_common.timezone_utils import timezone_at

from user_app.db.models import CustomEvent, CustomEventStatus
from user_app.services.custom_event_notifications import (
    notify_users_of_event_update,
    snapshot_custom_event,
)
from user_app.services.event_change_fields import detect_custom_event_changes
from user_app.services.event_cleanup_service import cleanup_custom_event_references
from user_app.services import reminder_service


class CustomEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        owner_user_id: uuid.UUID,
        title: str,
        short_title: str | None,
        description: str | None,
        venue: str,
        location: str,
        address_line: str | None,
        postal_code: str | None,
        lat: float,
        lng: float,
        category: str,
        category_color: str,
        price_label: str | None,
        image_url: str | None,
        tags: list,
        starts_at,
        ends_at,
        lineup: list,
        tickets: list,
        publish: bool,
    ) -> CustomEvent:
        event = CustomEvent(
            owner_user_id=owner_user_id,
            title=title,
            short_title=short_title,
            description=description,
            venue=venue,
            location=location,
            address_line=address_line,
            postal_code=postal_code,
            lat=lat,
            lng=lng,
            category=category,
            category_color=category_color,
            price_label=price_label,
            image_url=image_url,
            tags=tags,
            starts_at=starts_at,
            ends_at=ends_at,
            event_timezone=timezone_at(lat, lng),
            lineup=lineup,
            tickets=tickets,
            status=CustomEventStatus.PUBLISHED if publish else CustomEventStatus.DRAFT,
        )
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return self._load_with_owner(event.id) or event

    def get(self, event_id: uuid.UUID) -> CustomEvent | None:
        return self._load_with_owner(event_id)

    def list_for_owner(self, owner_user_id: uuid.UUID) -> list[CustomEvent]:
        stmt = (
            select(CustomEvent)
            .options(joinedload(CustomEvent.owner))
            .where(CustomEvent.owner_user_id == owner_user_id)
            .order_by(CustomEvent.starts_at.asc())
        )
        return list(self._session.scalars(stmt).unique().all())

    def list_published(self) -> list[CustomEvent]:
        stmt = (
            select(CustomEvent)
            .options(joinedload(CustomEvent.owner))
            .where(CustomEvent.status == CustomEventStatus.PUBLISHED)
            .order_by(CustomEvent.starts_at.asc())
        )
        return list(self._session.scalars(stmt).unique().all())

    def update(
        self,
        event_id: uuid.UUID,
        *,
        owner_user_id: uuid.UUID,
        **fields,
    ) -> CustomEvent | None:
        event = self._session.get(CustomEvent, event_id)
        if event is None or event.owner_user_id != owner_user_id:
            return None

        before = snapshot_custom_event(event)

        if "publish" in fields:
            publish = fields.pop("publish")
            if publish is not None:
                event.status = (
                    CustomEventStatus.PUBLISHED if publish else CustomEventStatus.DRAFT
                )

        for key, value in fields.items():
            if value is not None and hasattr(event, key):
                setattr(event, key, value)

        if "lat" in fields or "lng" in fields:
            event.event_timezone = timezone_at(event.lat, event.lng)

        changed_fields = detect_custom_event_changes(before, event)
        if changed_fields:
            if set(changed_fields) & {"date", "time", "title"}:
                reminder_service.refresh_custom_event_reminders(self._session, event)
            notify_users_of_event_update(
                self._session,
                event=event,
                changed_fields=changed_fields,
            )

        self._session.commit()
        return self._load_with_owner(event_id)

    def delete(self, event_id: uuid.UUID, *, owner_user_id: uuid.UUID) -> bool:
        event = self._session.get(CustomEvent, event_id)
        if event is None or event.owner_user_id != owner_user_id:
            return False
        cleanup_custom_event_references(
            self._session,
            event_id=event.id,
            event_title=event.title,
        )
        self._session.delete(event)
        self._session.commit()
        return True

    def _load_with_owner(self, event_id: uuid.UUID) -> CustomEvent | None:
        stmt = (
            select(CustomEvent)
            .options(joinedload(CustomEvent.owner))
            .where(CustomEvent.id == event_id)
        )
        return self._session.scalars(stmt).unique().first()
