"""Для чего нужен этот файл:
Собирает настройки из переменных окружения. Так адреса баз данных и другие параметры можно менять без правки исходного кода.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    mongodb_url: str = "mongodb://localhost:27017/notification_db"
    jwt_secret_key: str = "change-me-to-a-long-random-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    service_name: str = "notification-service"
    service_port: int = 8006

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
