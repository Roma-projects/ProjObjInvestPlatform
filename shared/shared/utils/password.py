"""Для чего нужен этот файл:
Хеширует пароли перед сохранением и проверяет введённый пароль при входе, не сохраняя исходный текст.
"""

"""Password hashing with bcrypt (12 rounds)."""

from passlib.context import CryptContext

from shared.config import get_shared_settings

_pwd_context: CryptContext | None = None


def _get_context() -> CryptContext:
    global _pwd_context
    if _pwd_context is None:
        rounds = get_shared_settings().bcrypt_rounds
        _pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=rounds,
        )
    return _pwd_context


def hash_password(password: str) -> str:
    return _get_context().hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _get_context().verify(plain_password, hashed_password)
