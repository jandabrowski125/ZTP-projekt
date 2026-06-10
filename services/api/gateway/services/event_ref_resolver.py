from uuid import UUID

from fastapi import HTTPException, status
from httpx import HTTPStatusError

from gateway.clients.events_client import EventsServiceClient
from gateway.dto.user_events import EventRefBody, EventTargetPayload


async def resolve_event_ref(
    ref: EventRefBody,
    events_client: EventsServiceClient,
) -> EventTargetPayload:
    if ref.community_event_id:
        custom_id = UUID(ref.community_event_id)
        try:
            snapshot = await events_client.get_event(ref.event_id)
        except HTTPStatusError:
            snapshot = None
        return EventTargetPayload(
            public_event_id=ref.event_id,
            provider="custom",
            external_id=ref.community_event_id,
            custom_event_id=custom_id,
            event_snapshot=snapshot,
        )

    try:
        snapshot = await events_client.get_event(ref.event_id)
    except HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from exc

    community_raw = snapshot.get("community_event_id")
    return EventTargetPayload(
        public_event_id=ref.event_id,
        provider=str(snapshot.get("provider") or ""),
        external_id=str(snapshot.get("external_id") or ""),
        custom_event_id=UUID(community_raw) if community_raw else None,
        event_snapshot=snapshot,
    )
