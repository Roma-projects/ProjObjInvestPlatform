from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    rabbitmq_url: str
    gateway_shared_secret: str = Field(min_length=32)
    auth_moderation_secret: str = Field(min_length=32)
    listing_moderation_secret: str = Field(min_length=32)
    listing_url: str = "http://listing-service:8000"
    auth_url: str = "http://auth-service:8000"
    log_level: str = "INFO"
    service_name: str = "moderation-service"


@lru_cache
def get_settings() -> Settings:
    return Settings()

