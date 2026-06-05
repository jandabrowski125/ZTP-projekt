import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

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

        if "publish" in fields:
            publish = fields.pop("publish")
            if publish is not None:
                event.status = (
                    CustomEventStatus.PUBLISHED if publish else CustomEventStatus.DRAFT
                )

        for key, value in fields.items():
            if value is not None and hasattr(event, key):
                setattr(event, key, value)

        self._session.commit()
        return self._load_with_owner(event_id)

    def delete(self, event_id: uuid.UUID, *, owner_user_id: uuid.UUID) -> bool:
        event = self._session.get(CustomEvent, event_id)
        if event is None or event.owner_user_id != owner_user_id:
            return False
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
