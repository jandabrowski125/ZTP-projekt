from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    events_service_url: str = "http://localhost:8001"
    user_service_url: str = "http://localhost:8002"
    cors_origins: str = "http://localhost:5173,http://localhost:5678"
    trusted_hosts: str = "*"
    trust_proxy_headers: bool = False
    internal_service_token: str = ""
    docs_username: str = "admin"
    docs_password: str = ""

    @field_validator("trust_proxy_headers", mode="before")
    @classmethod
    def parse_trust_proxy(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()
