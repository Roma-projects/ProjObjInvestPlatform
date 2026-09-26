"""Для чего нужен этот файл:
Описывает таблицы базы данных и их поля. ORM преобразует эти модели Python в записи базы данных и обратно.
"""

from shared.models.user import UserBase
from shared.models.listing import ListingBase

__all__ = ["UserBase", "ListingBase"]
