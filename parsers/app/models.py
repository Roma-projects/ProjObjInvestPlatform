"""Валидирует контракты задания и ответа Parsers перед работой с RabbitMQ."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ParserRequest(BaseModel):
    correlation_id: str
    reply_to: str
    listing_id: str
    fio: str = Field(min_length=3)
    inn: str = Field(pattern=r"^\d{12}$")
    status: Literal["ip", "self_employed"]
    ogrnip: str | None = None
    sources: list[Literal["egrul", "pb", "fedresurs", "kad"]] = ["egrul", "pb", "fedresurs", "kad"]
    ttl_seconds: int = Field(default=120, ge=1, le=300)

    @field_validator("ogrnip", mode="before")
    @classmethod
    def normalize_ogrnip(cls, value: Any) -> str | None:
        """Переводит числовой ОГРНИП из тестового JSON в строковый идентификатор."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError("ogrnip must be a string or integer")
        return str(value)


class ParserResponse(BaseModel):
    correlation_id: str
    listing_id: str
    status: Literal["ok", "not_found", "partial", "error"]
    registry_extract: dict[str, Any]
    files: dict[str, list[str]]
    metadata: dict[str, Any]
