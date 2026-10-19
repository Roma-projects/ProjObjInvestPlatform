"""HTTP read-management endpoints for Gateway; identity comes from its JWT claims."""

import hmac
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.config import get_settings
from app.store import store

settings = get_settings()
router = APIRouter(prefix="/messages", tags=["messaging"])


def _owner(request: Request) -> str:
    """Reads the trusted user UUID header which Gateway derived from the signed JWT."""
    supplied = request.headers.get("X-Gateway-Token", "")
    if not hmac.compare_digest(supplied, settings.gateway_shared_secret):
        raise HTTPException(status_code=403, detail="API Gateway required")
    try:
        return str(UUID(request.headers["X-Authenticated-User-ID"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Authenticated user is required") from exc


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def get_or_create_conversation(request: Request, body: dict) -> dict:
    owner = _owner(request)
    try:
        conversation = await store.get_or_create_conversation(owner, str(body["participant_id"]))
        return store._json_safe(conversation, owner)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="participant_id must be another user's UUID") from exc


@router.get("/conversations")
async def list_conversations(
    request: Request,
    cursor: str | None = None,
    filter: str = Query("all", pattern="^(all|unread)$"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    try:
        return await store.list_conversations(_owner(request), cursor, filter == "unread", limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


@router.get("/conversations/{conversation_id}/messages")
async def history(
    conversation_id: str,
    request: Request,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    try:
        return await store.history(_owner(request), conversation_id, cursor, limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


@router.delete("/{message_id}")
async def delete_message(message_id: str, request: Request, body: dict) -> dict:
    owner = _owner(request)
    deleted = await store.delete_message(owner, message_id, bool(body.get("delete_for_all", False)))
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found or not permitted")
    return {"deleted": True}


@router.post("/read")
async def mark_read(request: Request, body: dict) -> dict:
    owner = _owner(request)
    ids = body.get("message_ids")
    if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
        raise HTTPException(status_code=422, detail="message_ids must be an array of strings")
    return {"updated": await store.mark_read(owner, ids)}
