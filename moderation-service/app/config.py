from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/moderation_db"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    jwt_secret_key: str = "change-me-to-a-long-random-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    gateway_shared_secret: str = "local-gateway-secret-change-me"
    moderation_service_shared_secret: str = "local-moderation-secret-change-me"
    listing_url: str = "http://listing-service:8000"
    auth_url: str = "http://auth-service:8000"
    log_level: str = "INFO"
    service_name: str = "moderation-service"


@lru_cache
def get_settings() -> Settings:
    return Settings()

