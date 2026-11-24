"""Для чего нужен этот файл:
Собирает настройки из переменных окружения. Так адреса баз данных и другие параметры можно менять без правки исходного кода.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str
    rabbitmq_url: str
    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "./uploads"
    public_upload_dir: str = "/public_uploads"
    private_upload_dir: str = "/private_uploads"
    gateway_shared_secret: str = Field(min_length=32)
    moderation_service_shared_secret: str = Field(min_length=32)
    log_level: str = "INFO"
    service_name: str = "listing-service"
    service_port: int = 8002
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "real-estate-aggregator/1.0"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
