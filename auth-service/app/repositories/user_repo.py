"""Для чего нужен этот файл:
Собирает операции чтения и записи в базе данных, отделяя запросы к хранилищу от правил приложения.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone: str | None,
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        logger.info("User created id=%s email=%s", user.id, user.email)
        return user
