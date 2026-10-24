"""Настройки очередей, хранилищ и OpenAI-совместимой vision-модели Polza."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/analytic_ai_db"
    qwen_base_url: str = ""
    qwen_api_key: str = ""
    qwen_model: str = "Qwen2.5-VL-7B-Instruct"
    polza_base_url: str = "https://polza.ai/api/v1"
    polza_api_key: str = ""
    polza_model: str = "google/gemini-3.8-flash"
    public_upload_dir: str = "/public_uploads"
    model_timeout_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
