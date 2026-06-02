from events_app.domain.models import Category

DEFAULT_CATEGORIES: tuple[Category, ...] = (
    Category("All Events", "event"),
    Category("Music", "music_note"),
    Category("Food & Drink", "restaurant"),
    Category("Sports", "sports_soccer"),
    Category("Arts", "palette"),
    Category("Nightlife", "nightlife"),
)
