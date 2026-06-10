import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from user_app.db.models import UserNotification


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, user_id: uuid.UUID) -> list[UserNotification]:
        now = datetime.now(UTC)
        stmt = (
            select(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.scheduled_for <= now,
            )
            .order_by(UserNotification.scheduled_for.desc())
        )
        return list(self._session.scalars(stmt).all())

    def unread_count(self, user_id: uuid.UUID) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.scheduled_for <= now,
                UserNotification.read.is_(False),
            )
        )
        return int(self._session.scalar(stmt) or 0)

    def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
        row = self._session.get(UserNotification, notification_id)
        if row is None or row.user_id != user_id:
            return False
        row.read = True
        self._session.commit()
        return True

    def mark_all_read(self, user_id: uuid.UUID) -> int:
        now = datetime.now(UTC)
        rows = list(
            self._session.scalars(
                select(UserNotification).where(
                    UserNotification.user_id == user_id,
                    UserNotification.scheduled_for <= now,
                    UserNotification.read.is_(False),
                )
            ).all()
        )
        for row in rows:
            row.read = True
        self._session.commit()
        return len(rows)

    def delete_all_for_user(self, user_id: uuid.UUID) -> int:
        rows = list(
            self._session.scalars(
                select(UserNotification).where(UserNotification.user_id == user_id)
            ).all()
        )
        for row in rows:
            self._session.delete(row)
        self._session.commit()
        return len(rows)
