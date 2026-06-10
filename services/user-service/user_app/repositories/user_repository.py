import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from user_app.db.models import SavedEventListType, User, UserSavedEvent
from user_app.schemas.user_events import EventTargetRequest
from user_app.schemas.users import UserPreferences


class UserAlreadyExistsError(Exception):
    pass


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        username: str,
        full_name: str,
        bio: str | None,
        location: str | None,
        avatar_url: str | None,
        preferences: dict,
        firebase_uid: str | None = None,
    ) -> User:
        user = User(
            email=email.lower(),
            firebase_uid=firebase_uid,
            password_hash=password_hash,
            username=username,
            full_name=full_name,
            bio=bio,
            location=location,
            avatar_url=avatar_url,
            preferences=preferences,
        )
        self._session.add(user)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise UserAlreadyExistsError from exc
        self._session.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self._session.scalars(stmt).first()

    def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        stmt = select(User).where(User.firebase_uid == firebase_uid)
        return self._session.scalars(stmt).first()

    def link_firebase_uid(self, user: User, firebase_uid: str) -> User:
        user.firebase_uid = firebase_uid
        self._session.commit()
        self._session.refresh(user)
        return user

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self._session.scalars(stmt).first()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._session.get(User, user_id)

    def update_user(self, user: User, **fields: object) -> User:
        for key, value in fields.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        self._session.commit()
        self._session.refresh(user)
        return user

    def list_saved_events(
        self,
        user_id: uuid.UUID,
        list_type: SavedEventListType,
    ) -> list[UserSavedEvent]:
        stmt = (
            select(UserSavedEvent)
            .where(
                UserSavedEvent.user_id == user_id,
                UserSavedEvent.list_type == list_type,
            )
            .order_by(UserSavedEvent.created_at.desc())
        )
        return list(self._session.scalars(stmt).all())

    def _saved_event_lookup(
        self,
        user_id: uuid.UUID,
        list_type: SavedEventListType,
        target: EventTargetRequest,
    ):
        if target.custom_event_id is not None:
            return select(UserSavedEvent).where(
                UserSavedEvent.user_id == user_id,
                UserSavedEvent.list_type == list_type,
                UserSavedEvent.custom_event_id == target.custom_event_id,
            )
        return select(UserSavedEvent).where(
            UserSavedEvent.user_id == user_id,
            UserSavedEvent.list_type == list_type,
            UserSavedEvent.public_event_id == target.public_event_id,
            UserSavedEvent.provider == target.provider,
            UserSavedEvent.external_id == target.external_id,
        )

    def has_saved_event(
        self,
        user_id: uuid.UUID,
        list_type: SavedEventListType,
        target: EventTargetRequest,
    ) -> bool:
        return self._session.scalars(self._saved_event_lookup(user_id, list_type, target)).first() is not None

    def add_saved_event(
        self,
        *,
        user_id: uuid.UUID,
        list_type: SavedEventListType,
        target: EventTargetRequest,
        attended_at=None,
    ) -> UserSavedEvent:
        row = UserSavedEvent(
            user_id=user_id,
            list_type=list_type,
            public_event_id=target.public_event_id,
            provider=target.provider,
            external_id=target.external_id,
            custom_event_id=target.custom_event_id,
            event_snapshot=None,
            attended_at=attended_at,
        )
        self._session.add(row)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            existing = self._session.scalars(
                self._saved_event_lookup(user_id, list_type, target)
            ).first()
            if existing is None:
                raise
            return existing
        self._session.refresh(row)
        return row

    def add_saved_aggregated_event(
        self,
        *,
        user_id: uuid.UUID,
        list_type: SavedEventListType,
        public_event_id: int,
        provider: str,
        external_id: str,
        event_snapshot: dict | None,
        attended_at,
    ) -> UserSavedEvent:
        return self.add_saved_event(
            user_id=user_id,
            list_type=list_type,
            target=EventTargetRequest(
                public_event_id=public_event_id,
                provider=provider,
                external_id=external_id,
                event_snapshot=event_snapshot,
            ),
            attended_at=attended_at,
        )

    def remove_saved_event_by_ref(
        self,
        user_id: uuid.UUID,
        list_type: SavedEventListType,
        target: EventTargetRequest,
    ) -> bool:
        row = self._session.scalars(self._saved_event_lookup(user_id, list_type, target)).first()
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True

    def remove_saved_event(self, user_id: uuid.UUID, saved_id: uuid.UUID) -> bool:
        row = self._session.get(UserSavedEvent, saved_id)
        if row is None or row.user_id != user_id:
            return False
        self._session.delete(row)
        self._session.commit()
        return True


def preferences_to_dict(prefs: UserPreferences | None) -> dict:
    if prefs is None:
        return UserPreferences().model_dump()
    return prefs.model_dump()
