"""Для чего нужен этот файл:
Собирает настройки из переменных окружения. Так адреса баз данных и другие параметры можно менять без правки исходного кода.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis_url: str = "redis://localhost:6379/0"
    gateway_shared_secret: str = "local-gateway-secret-change-me"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    mongodb_url: str = "mongodb://localhost:27017/search_catalog"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    service_name: str = "search-service"
    service_port: int = 8003
    cache_ttl_seconds: int = 60
    nominatim_base_url: str = "https://nominatim.openstreetmap.org/search"
    nominatim_user_agent: str = "MieroVenture/1.0"
    nominatim_enabled: bool = True
    nominatim_min_interval_ms: int = 1100

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
