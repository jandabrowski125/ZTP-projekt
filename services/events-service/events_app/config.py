from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    events_service_host: str = "0.0.0.0"
    events_service_port: int = 8001
    internal_service_token: str = ""
    docs_username: str = "admin"
    docs_password: str = ""

    # Default map/search center (Kraków, Rynek Główny)
    default_coord_lat: float = 50.046943
    default_coord_lng: float = 19.997153

    # Optional per-provider overrides (inherit DEFAULT_COORD_* when unset)
    ticketmaster_lat: float | None = Field(default=None)
    ticketmaster_lng: float | None = Field(default=None)

    ticketmaster_api_key: str = ""
    ticketmaster_radius: int = 50
    ticketmaster_unit: str = "km"
    ticketmaster_country_code: str = "PL"
    ticketmaster_locale: str = "pl-pl"
    ticketmaster_page_size: int = 50
    ticketmaster_base_url: str = "https://app.ticketmaster.com/discovery/v2"
    # Dedupe parallel /events + /map/pins calls; TM free tier is ~5 req/s with burst 1.
    ticketmaster_cache_ttl_seconds: float = 60.0

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

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


settings = Settings()
