"""Для чего нужен этот файл:
Собирает настройки из переменных окружения. Так адреса баз данных и другие параметры можно менять без правки исходного кода.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mongodb_url: str = "mongodb://localhost:27017/messaging_db"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    gateway_shared_secret: str
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    service_name: str = "messaging-service"
    service_port: int = 8004

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
