"""Для чего нужен этот файл:
Создаёт подключение к базе данных и общие средства работы с сессиями — временными каналами для чтения и изменения данных.
"""

"""Async SQLAlchemy base helpers for microservices."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all service models."""


def create_engine(database_url: str, **kwargs: Any) -> AsyncEngine:
    return create_async_engine(
        database_url,
        echo=kwargs.pop("echo", False),
        pool_pre_ping=True,
        **kwargs,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
