from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    events_service_host: str = "0.0.0.0"
    events_service_port: int = 8001

    # Default map/search center (Kraków, Rynek Główny)
    default_coord_lat: float = 50.046943
    default_coord_lng: float = 19.997153

    # Optional per-provider overrides (inherit DEFAULT_COORD_* when unset)
    ticketmaster_lat: float | None = Field(default=None)
    ticketmaster_lng: float | None = Field(default=None)
    eventbrite_lat: float | None = Field(default=None)
    eventbrite_lng: float | None = Field(default=None)

    ticketmaster_api_key: str = ""
    ticketmaster_radius: int = 50
    ticketmaster_unit: str = "km"
    ticketmaster_country_code: str = "PL"
    ticketmaster_locale: str = "pl-pl"
    ticketmaster_page_size: int = 50
    ticketmaster_base_url: str = "https://app.ticketmaster.com/discovery/v2"
    # Dedupe parallel /events + /map/pins calls; TM free tier is ~5 req/s with burst 1.
    ticketmaster_cache_ttl_seconds: float = 60.0

    eventbrite_token: str = ""
    # Required for EventBrite list data (public /events/search/ returns 404/406)
    eventbrite_organization_id: str = ""
    eventbrite_radius: int = 50
    eventbrite_unit: str = "km"
    eventbrite_page_size: int = 50
    eventbrite_base_url: str = "https://www.eventbriteapi.com/v3"
    eventbrite_cache_ttl_seconds: float = 60.0

    @property
    def ticketmaster_search_lat(self) -> float:
        return (
            self.ticketmaster_lat if self.ticketmaster_lat is not None else self.default_coord_lat
        )

    @property
    def ticketmaster_search_lng(self) -> float:
        return (
            self.ticketmaster_lng if self.ticketmaster_lng is not None else self.default_coord_lng
        )

    @property
    def eventbrite_search_lat(self) -> float:
        return (
            self.eventbrite_lat if self.eventbrite_lat is not None else self.default_coord_lat
        )

    @property
    def eventbrite_search_lng(self) -> float:
        return (
            self.eventbrite_lng if self.eventbrite_lng is not None else self.default_coord_lng
        )


settings = Settings()
