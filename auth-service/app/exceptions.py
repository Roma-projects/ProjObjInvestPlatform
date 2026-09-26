"""Для чего нужен этот файл:
Описывает ошибки приложения и правила превращения их в понятные HTTP-ответы.
"""

class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=409)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, status_code=404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403)
