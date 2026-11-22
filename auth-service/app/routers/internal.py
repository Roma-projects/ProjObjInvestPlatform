import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User

settings = get_settings()
router = APIRouter(prefix="/internal/auth", tags=["internal auth"])


@router.get("/users/{user_id}")
async def resolve_user_identity(user_id: UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict:
    """Resolve the stable public UUID to the legacy integer owner ID for trusted services."""
    supplied = request.headers.get("X-Moderation-Token", "")
    if not hmac.compare_digest(supplied, settings.moderation_service_shared_secret):
        raise HTTPException(status_code=403, detail="Moderation service required")
    user = await session.scalar(select(User).where(User.user_id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": str(user.user_id), "legacy_user_id": user.id}

