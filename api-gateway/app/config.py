"""Настройки адресов внутренних сервисов и общей проверки JWT."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_public_key_b64: str = Field(min_length=256)
    jwt_algorithm: Literal["RS256"] = "RS256"
    redis_url: str
    rabbitmq_url: str
    auth_gateway_secret: str = Field(min_length=32)
    listing_gateway_secret: str = Field(min_length=32)
    search_gateway_secret: str = Field(min_length=32)
    notification_gateway_secret: str = Field(min_length=32)
    messaging_gateway_secret: str = Field(min_length=32)
    moderation_gateway_secret: str = Field(min_length=32)
    auth_url: str = "http://auth-service:8000"
    listing_url: str = "http://listing-service:8000"
    search_url: str = "http://search-service:8000"
    notification_url: str = "http://notification-service:8000"
    messaging_url: str = "http://messaging-service:8000"
    moderation_url: str = "http://moderation-service:8000"
    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 15
    upload_rate_limit_per_minute: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
