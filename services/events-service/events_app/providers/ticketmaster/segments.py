"""Ticketmaster classification segment IDs (locale-independent)."""

from events_app.domain.models import MapPinCategory

# https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/#segment-object
SEGMENT_ID_TO_CATEGORY: dict[str, str] = {
    "KZFzniwnSyZfZ7v7n1": "Other",  # Miscellaneous
    "KZFzniwnSyZfZ7v7nJ": "Music",
    "KZFzniwnSyZfZ7v7nE": "Sports",
    "KZFzniwnSyZfZ7v7na": "Arts & Theatre",
}

CATEGORY_COLORS: dict[str, str] = {
    "Music": "#7c3aed",
    "Sports": "#4ade80",
    "Arts & Theatre": "#0ea5e9",
    "Other": "#958da1",
}

CATEGORY_TO_PIN: dict[str, MapPinCategory] = {
    "Music": MapPinCategory.MUSIC,
    "Sports": MapPinCategory.SPORTS,
    "Arts & Theatre": MapPinCategory.DEFAULT,
    "Other": MapPinCategory.DEFAULT,
}
