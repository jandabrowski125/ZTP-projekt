from gateway.dto.users import SavedEventDTO, UserPreferencesDTO, UserProfileDTO


def to_user_profile_dto(raw: dict) -> UserProfileDTO:
    prefs = raw.get("preferences") or {}
    return UserProfileDTO(
        id=raw["id"],
        email=raw["email"],
        username=raw["username"],
        fullName=raw["full_name"],
        bio=raw.get("bio"),
        location=raw.get("location"),
        avatarUrl=raw.get("avatar_url"),
        createdAt=raw["created_at"],
        preferences=UserPreferencesDTO(
            eventReminders=prefs.get("event_reminders", True),
            newEvents=prefs.get("new_events", True),
            friendActivity=prefs.get("friend_activity", False),
            promotions=prefs.get("promotions", False),
            privateProfile=prefs.get("private_profile", False),
        ),
    )


def to_saved_event_dto(raw: dict) -> SavedEventDTO:
    return SavedEventDTO(
        id=raw["id"],
        listType=raw["list_type"],
        publicEventId=raw.get("public_event_id"),
        provider=raw.get("provider"),
        externalId=raw.get("external_id"),
        customEventId=raw.get("custom_event_id"),
        eventSnapshot=raw.get("event_snapshot"),
        attendedAt=raw.get("attended_at"),
    )


def update_body_to_snake(body: dict) -> dict:
    payload: dict = {}
    if "fullName" in body and body["fullName"] is not None:
        payload["full_name"] = body["fullName"]
    if "bio" in body:
        payload["bio"] = body["bio"]
    if "location" in body:
        payload["location"] = body["location"]
    if "avatarUrl" in body:
        payload["avatar_url"] = body["avatarUrl"]
    if body.get("preferences") is not None:
        prefs = body["preferences"]
        payload["preferences"] = {
            "event_reminders": prefs.get("eventReminders", prefs.get("event_reminders", True)),
            "new_events": prefs.get("newEvents", prefs.get("new_events", True)),
            "friend_activity": prefs.get("friendActivity", prefs.get("friend_activity", False)),
            "promotions": prefs.get("promotions", False),
            "private_profile": prefs.get("privateProfile", prefs.get("private_profile", False)),
        }
    return payload
