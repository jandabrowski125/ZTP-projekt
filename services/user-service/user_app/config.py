from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    user_service_host: str = "0.0.0.0"
    user_service_port: int = 8002
    internal_service_token: str = ""
    docs_username: str = "admin"
    docs_password: str = ""

    database_url: str = Field(
        default="postgresql+psycopg://eventradar:eventradar@localhost:5432/eventradar",
        description="PostgreSQL URL (cloud or local). Use sqlite only in tests.",
    )
    database_echo: bool = False

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()
