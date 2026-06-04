from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    events_service_url: str = "http://localhost:8001"
    user_service_url: str = "http://localhost:8002"
    cors_origins: str = "http://localhost:5173,http://localhost:5678"


settings = Settings()
