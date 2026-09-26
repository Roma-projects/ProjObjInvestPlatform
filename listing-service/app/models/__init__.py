"""Для чего нужен этот файл:
Описывает таблицы базы данных и их поля. ORM преобразует эти модели Python в записи базы данных и обратно.
"""

from app.models.listing import Listing, Photo

__all__ = ["Listing", "Photo"]
