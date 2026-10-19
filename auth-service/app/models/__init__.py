"""Для чего нужен этот файл:
Описывает таблицы базы данных и их поля. ORM преобразует эти модели Python в записи базы данных и обратно.
"""

from app.models.user import User

__all__ = ["User"]
"""Экспорт моделей Auth для их регистрации в метаданных SQLAlchemy."""

from app.models.session import AuthSession
from app.models.user import User

__all__ = ["AuthSession", "User"]
