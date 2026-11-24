"""Для чего нужен этот файл:
Собирает настройки из переменных окружения. Так адреса баз данных и другие параметры можно менять без правки исходного кода.
"""

import base64
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_private_key_b64: str = Field(min_length=256)
    jwt_public_key_b64: str = Field(min_length=256)
    jwt_algorithm: Literal["RS256"] = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    bcrypt_rounds: int = 12
    redis_url: str
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""
    smtp_start_tls: bool = True
    refresh_cookie_secure: bool = True
    verification_code_ttl_seconds: int = 600
    gateway_shared_secret: str = Field(min_length=32)
    moderation_service_shared_secret: str = Field(min_length=32)
    rabbitmq_url: str
    cors_origins: str = "http://localhost:3000"
    avatar_upload_dir: str = "/auth_avatars"
    log_level: str = "INFO"
    service_name: str = "auth-service"
    service_port: int = 8001

    @property
    def jwt_private_key(self) -> bytes:
        return base64.b64decode(self.jwt_private_key_b64, validate=True)

    @property
    def jwt_public_key(self) -> bytes:
        return base64.b64decode(self.jwt_public_key_b64, validate=True)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
