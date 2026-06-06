from events_app.domain.models import Category

# Icon metadata for known TM segment IDs (labels match mapper SEGMENT_ID_TO_CATEGORY).
DEFAULT_CATEGORIES: tuple[Category, ...] = (
    Category("All Events", "event"),
    Category("Music", "music_note"),
    Category("Sports", "sports_soccer"),
    Category("Arts & Theatre", "theater_comedy"),
    Category("Other", "category"),
)
