from datetime import date

from events_app.domain.models import Category, Event, LineupArtist, MapPinCategory, Ticket
from events_app.repositories.protocol import EventRepository

_DEFAULT_LINEUP = (
    LineupArtist("Charlotte de Witte", "Headliner", "#89ceff", ""),
    LineupArtist("Amelie Lens", "", "", "02:00 AM"),
    LineupArtist("Enrico Sangiuliano", "", "", "12:00 AM"),
    LineupArtist("SPFDJ", "", "", "10:00 PM"),
)

_DEFAULT_TICKETS = (
    Ticket("local_activity", "#89ceff", "General Admission", "Tier 2 Available", "$65", "#89ceff"),
    Ticket("star", "#d2bbff", "VIP Access", "Skip the line + Balcony", "$120", "#d2bbff"),
    Ticket(
        "workspace_premium",
        "#ffb784",
        "Ultra VIP",
        "Private area + Open bar",
        "$220",
        "#ffb784",
    ),
)

_MOCK_EVENTS: tuple[Event, ...] = (
    Event(
        id=1,
        title="Electric Nights Techno Festival",
        short_title="Electric Nights",
        month="OCT",
        day="24",
        time="10:00 PM – 6:00 AM",
        day_label="Friday, Oct 24",
        venue="The Warehouse",
        location="Brooklyn, NY",
        distance="0.5 mi",
        category="Music",
        category_color="#7c3aed",
        price="$65",
        image="https://images.unsplash.com/photo-1773385404894-104116c1ef31?w=1080&q=80",
        tags=("Techno", "Underground", "21+"),
        lat=40.6975,
        lng=-73.9742,
        map_pin_category=MapPinCategory.MUSIC,
        featured=True,
        event_date=date(2025, 10, 24),
        description=(
            "A night of underground techno in Brooklyn's iconic warehouse district. "
            "World-class DJs, immersive visuals, and a crowd that lives for the beat."
        ),
        lineup=_DEFAULT_LINEUP,
        tickets=_DEFAULT_TICKETS,
    ),
    Event(
        id=2,
        title="Neon Dreams Brooklyn",
        short_title="Neon Dreams",
        month="NOV",
        day="12",
        time="9:00 PM – 4:00 AM",
        day_label="Wed, Nov 12",
        venue="Brooklyn Navy Yard",
        location="Brooklyn, NY",
        distance="1.2 mi",
        category="Nightlife",
        category_color="#00a2e6",
        price="$45",
        image="https://images.unsplash.com/photo-1751071479001-480c55fb1d0d?w=1080&q=80",
        tags=("Electronic", "Dance", "21+"),
        lat=40.6978,
        lng=-73.9701,
        map_pin_category=MapPinCategory.MUSIC,
        featured=False,
        event_date=date(2025, 11, 12),
        description="Neon-soaked electronic dance night at the Navy Yard with top regional DJs.",
        lineup=_DEFAULT_LINEUP,
        tickets=_DEFAULT_TICKETS,
    ),
    Event(
        id=3,
        title="Night Market Bites",
        short_title="Night Market",
        month="OCT",
        day="25",
        time="7:00 PM – 11:00 PM",
        day_label="Tonight, 7:00 PM",
        venue="Pier 39",
        location="Manhattan, NY",
        distance="1.2 mi",
        category="Food & Drink",
        category_color="#ffb784",
        price="Free",
        image="https://images.unsplash.com/photo-1549366970-6b64335a55cb?w=1080&q=80",
        tags=("Street Food", "Outdoor"),
        lat=40.7549,
        lng=-73.9840,
        map_pin_category=MapPinCategory.FOOD,
        featured=False,
        event_date=date(2025, 10, 25),
        description="Open-air night market with street food vendors from across NYC.",
        lineup=(),
        tickets=(
            Ticket("restaurant", "#ffb784", "General Entry", "Free admission", "Free", "#ffb784"),
        ),
    ),
    Event(
        id=4,
        title="City Derby Match",
        short_title="City Derby",
        month="OCT",
        day="26",
        time="8:00 PM",
        day_label="Oct 26, 8:00 PM",
        venue="Main Stadium",
        location="Queens, NY",
        distance="3.0 mi",
        category="Sports",
        category_color="#4ade80",
        price="$30",
        image="https://images.unsplash.com/photo-1767397194546-c51509f4a715?w=1080&q=80",
        tags=("Soccer", "Live Sport"),
        lat=40.7337,
        lng=-73.8740,
        map_pin_category=MapPinCategory.SPORTS,
        featured=False,
        event_date=date(2025, 10, 26),
        description="Rival clubs face off in the season's biggest local derby.",
        lineup=(),
        tickets=(
            Ticket("stadium", "#4ade80", "Standard Seat", "Upper tier", "$30", "#4ade80"),
            Ticket("star", "#d2bbff", "Premium Seat", "Lower tier + lounge", "$75", "#d2bbff"),
        ),
    ),
    Event(
        id=5,
        title="Warehouse Project NY",
        short_title="Warehouse Project",
        month="NOV",
        day="19",
        time="11:00 PM – 7:00 AM",
        day_label="Sat, Nov 19",
        venue="Secret Location",
        location="Brooklyn, NY",
        distance="0.8 mi",
        category="Music",
        category_color="#7c3aed",
        price="$80",
        image="https://images.unsplash.com/photo-1685435887020-eb43be863347?w=1080&q=80",
        tags=("Techno", "Dark", "21+"),
        lat=40.7020,
        lng=-73.9650,
        map_pin_category=MapPinCategory.MUSIC,
        featured=False,
        event_date=date(2025, 11, 19),
        description="All-night warehouse rave — location revealed 24h before doors.",
        lineup=_DEFAULT_LINEUP,
        tickets=_DEFAULT_TICKETS,
    ),
    Event(
        id=6,
        title="AI Summit NYC",
        short_title="AI Summit",
        month="NOV",
        day="8",
        time="10:00 AM – 6:00 PM",
        day_label="Sat, Nov 8",
        venue="Javits Center",
        location="Manhattan, NY",
        distance="2.1 mi",
        category="Arts",
        category_color="#0ea5e9",
        price="Free",
        image="https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=1080&q=80",
        tags=("Tech", "Talks", "Networking"),
        lat=40.7580,
        lng=-74.0020,
        map_pin_category=MapPinCategory.TECH,
        featured=False,
        event_date=date(2025, 11, 8),
        description="Talks and workshops on applied AI from industry leaders.",
        lineup=(),
        tickets=(
            Ticket("computer", "#0ea5e9", "Free Registration", "Limited seats", "Free", "#0ea5e9"),
        ),
    ),
)

_CATEGORIES: tuple[Category, ...] = (
    Category("All Events", "event"),
    Category("Music", "music_note"),
    Category("Food & Drink", "restaurant"),
    Category("Sports", "sports_soccer"),
    Category("Arts", "palette"),
    Category("Nightlife", "nightlife"),
)


class MockEventRepository(EventRepository):
    def __init__(self, events: tuple[Event, ...] = _MOCK_EVENTS) -> None:
        self._events = events

    def list_events(
        self,
        *,
        category: str | None = None,
        location: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        query: str | None = None,
        sort: str = "date_asc",
        lat: float | None = None,
        lng: float | None = None,
    ) -> list[Event]:
        del lat, lng
        results = list(self._events)

        if category and category != "All Events":
            results = [e for e in results if e.category == category]

        if location:
            needle = location.lower()
            results = [
                e for e in results if needle in e.location.lower() or needle in e.venue.lower()
            ]

        if date_from:
            results = [e for e in results if e.event_date >= date_from]

        if date_to:
            results = [e for e in results if e.event_date <= date_to]

        if query:
            needle = query.lower()
            results = [
                e
                for e in results
                if needle in e.title.lower()
                or needle in e.short_title.lower()
                or any(needle in tag.lower() for tag in e.tags)
            ]

        if sort == "date_desc":
            results.sort(key=lambda e: e.event_date, reverse=True)
        elif sort == "price_asc":
            results.sort(key=lambda e: _price_sort_key(e.price))
        else:
            results.sort(key=lambda e: e.event_date)

        return results

    def get_event(self, event_id: int) -> Event | None:
        return next((e for e in self._events if e.id == event_id), None)

    def list_categories(self) -> list[Category]:
        return list(_CATEGORIES)


def _price_sort_key(price: str) -> float:
    if price.lower() == "free":
        return 0.0
    digits = "".join(ch for ch in price if ch.isdigit() or ch == ".")
    return float(digits) if digits else 9999.0
