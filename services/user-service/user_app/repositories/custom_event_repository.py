import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from user_app.db.models import CustomEvent, CustomEventStatus


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
            lat=lat,
            lng=lng,
            category=category,
            category_color=category_color,
            price_label=price_label,
            image_url=image_url,
            tags=tags,
            starts_at=starts_at,
            ends_at=ends_at,
            lineup=lineup,
            tickets=tickets,
            status=CustomEventStatus.PUBLISHED if publish else CustomEventStatus.DRAFT,
        )
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

    def get(self, event_id: uuid.UUID) -> CustomEvent | None:
        return self._session.get(CustomEvent, event_id)

    def list_for_owner(self, owner_user_id: uuid.UUID) -> list[CustomEvent]:
        stmt = (
            select(CustomEvent)
            .where(CustomEvent.owner_user_id == owner_user_id)
            .order_by(CustomEvent.starts_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_published(self) -> list[CustomEvent]:
        stmt = (
            select(CustomEvent)
            .where(CustomEvent.status == CustomEventStatus.PUBLISHED)
            .order_by(CustomEvent.starts_at.asc())
        )
        return list(self._session.scalars(stmt).all())
