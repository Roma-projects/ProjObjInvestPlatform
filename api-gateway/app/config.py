"""Настройки адресов внутренних сервисов и общей проверки JWT."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    gateway_shared_secret: str
    auth_url: str = "http://auth-service:8000"
    listing_url: str = "http://listing-service:8000"
    search_url: str = "http://search-service:8000"
    notification_url: str = "http://notification-service:8000"
    messaging_url: str = "http://messaging-service:8000"
    moderation_url: str = "http://moderation-service:8000"
    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
