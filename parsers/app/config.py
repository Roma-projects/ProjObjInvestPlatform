"""Настройки источников, очередей, базы документов и локального файлового volume."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mongodb_url: str
    rabbitmq_url: str
    parsers_storage_dir: str = "./parsers_storage"
    egrul_url: str = "https://egrul.nalog.ru/"
    pb_url: str = "https://pb.nalog.ru/"
    fedresurs_url: str = "https://fedresurs.ru/"
    kad_url: str = "https://kad.arbitr.ru/"
    request_timeout_seconds: int = 20


@lru_cache
def get_settings() -> Settings:
    """Загружает настройки один раз и повторно использует их в приложении."""
    return Settings()
