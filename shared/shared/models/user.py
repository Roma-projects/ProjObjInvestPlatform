"""Для чего нужен этот файл:
Описывает таблицы базы данных и их поля. ORM преобразует эти модели Python в записи базы данных и обратно.
"""

"""Shared User DTO (not a SQLAlchemy model)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
