import hmac
from uuid import UUID

from fastapi import HTTPException, Request, status

from app.config import get_settings

settings = get_settings()


async def require_gateway(request: Request) -> None:
    supplied = request.headers.get("X-Gateway-Token", "")
    if not hmac.compare_digest(supplied, settings.gateway_shared_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Gateway required")


async def require_moderator(request: Request) -> dict:
    """Use identity claims only after the Gateway's per-service secret check."""
    if request.headers.get("X-Authenticated-User-Role") != "moderator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator role required")
    try:
        moderator_id = UUID(request.headers.get("X-Authenticated-User-ID", ""))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway user identity is invalid") from exc
    return {"moderator_id": moderator_id}

