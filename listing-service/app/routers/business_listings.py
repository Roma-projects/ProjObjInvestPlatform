"""Внешний контракт объявлений о продаже готового бизнеса."""

import base64
from datetime import datetime
from uuid import UUID

import hmac
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_uuid, require_gateway
from app.models.business_listing import BusinessListing
from app.schemas.business_listing import (
    BusinessListingDetail,
    BusinessListingDraft,
    BusinessListingResponse,
    CursorListingResponse,
)
from app.services.business_listing_service import PRIVATE_FIELDS, BusinessListingService
from app.config import get_settings

router = APIRouter(prefix="/listings", tags=["business listings"], dependencies=[Depends(require_gateway)])
internal_router = APIRouter(prefix="/internal/listings", tags=["private listing files"])
settings = get_settings()


def _detail(row: BusinessListing) -> BusinessListingDetail:
    data = {key: getattr(row, key) for key in BusinessListingDraft.model_fields if hasattr(row, key)}
    data.update({
        "id": row.id,
        "status": row.status,
        "verification_status": row.verification_status,
        "files": row.files or {},
        # Never return private storage paths from Listing's owner-facing API.
        "document_fields": sorted((row.documents or {}).keys()),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    })
    return BusinessListingDetail.model_validate(data)


def _encode_cursor(row: BusinessListing) -> str:
    raw = f"{row.created_at.isoformat()}|{row.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        created, listing_id = raw.rsplit("|", 1)
        return datetime.fromisoformat(created), UUID(listing_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


@router.post("", response_model=BusinessListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    body: BusinessListingDraft,
    user_id: UUID = Depends(get_current_user_uuid),
    session: AsyncSession = Depends(get_db),
) -> BusinessListingResponse:
    return await BusinessListingService(session).create_draft(user_id, body)


@router.get("", response_model=CursorListingResponse)
async def list_my_listings(
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user_id: UUID = Depends(get_current_user_uuid),
    session: AsyncSession = Depends(get_db),
) -> CursorListingResponse:
    query = select(BusinessListing).where(BusinessListing.user_id == user_id)
    if cursor:
        created, listing_id = _decode_cursor(cursor)
        query = query.where(or_(BusinessListing.created_at < created, and_(BusinessListing.created_at == created, BusinessListing.id < listing_id)))
    rows = list((await session.scalars(query.order_by(BusinessListing.created_at.desc(), BusinessListing.id.desc()).limit(limit + 1))).all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    return CursorListingResponse(items=[_detail(row) for row in rows], next_cursor=_encode_cursor(rows[-1]) if has_more and rows else None)


@router.get("/{listing_id}", response_model=BusinessListingDetail)
async def get_listing(
    listing_id: UUID,
    user_id: UUID = Depends(get_current_user_uuid),
    session: AsyncSession = Depends(get_db),
) -> BusinessListingDetail:
    return _detail(await BusinessListingService(session).get(user_id, listing_id))


@router.patch("/{listing_id}", response_model=BusinessListingResponse)
async def update_listing(
    listing_id: UUID,
    body: BusinessListingDraft,
    user_id: UUID = Depends(get_current_user_uuid),
    session: AsyncSession = Depends(get_db),
) -> BusinessListingResponse:
    return await BusinessListingService(session).update_draft(user_id, listing_id, body)


@router.post("/{listing_id}/files/{field}", status_code=status.HTTP_201_CREATED)
async def upload_listing_file(
    listing_id: UUID,
    field: str,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_uuid),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await BusinessListingService(session).upload_file(user_id, listing_id, field, file)


@router.post("/{listing_id}/submit", response_model=BusinessListingResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_listing(
    listing_id: UUID,
    user_id: UUID = Depends(get_current_user_uuid),
    session: AsyncSession = Depends(get_db),
) -> BusinessListingResponse:
    return await BusinessListingService(session).submit(user_id, listing_id)


async def require_moderation_service(request: Request) -> None:
    supplied = request.headers.get("X-Moderation-Token", "")
    if not hmac.compare_digest(supplied, settings.moderation_service_shared_secret):
        raise HTTPException(status_code=403, detail="Moderation service required")


@internal_router.get("/{listing_id}/documents/{field}", dependencies=[Depends(require_moderation_service)])
async def get_private_document(
    listing_id: UUID,
    field: str,
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    if field not in PRIVATE_FIELDS:
        raise HTTPException(status_code=404, detail="Document not found")
    row = await session.get(BusinessListing, listing_id)
    relative = (row.documents or {}).get(field) if row else None
    if not relative:
        raise HTTPException(status_code=404, detail="Document not found")
    root = Path(settings.private_upload_dir).resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        path,
        media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        filename=f"{field}{path.suffix.lower()}",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
