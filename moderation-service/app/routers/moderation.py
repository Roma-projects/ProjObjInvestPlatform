from collections.abc import AsyncIterator
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_gateway, require_moderator
from app.models import BlacklistEntry, ModerationCase
from app.schemas.moderation import (
    BlacklistCreate,
    BlacklistEntryRead,
    CatalogRemovalBody,
    DecisionBody,
    ModerationCaseRead,
)
from app.services.moderation_service import ModerationService

settings = get_settings()
router = APIRouter(prefix="/api/v1/moderation", tags=["moderation"], dependencies=[Depends(require_gateway)])


def _case_read(case: ModerationCase) -> ModerationCaseRead:
    return ModerationCaseRead(
        id=case.id,
        listing_id=case.listing_id,
        seller_id=case.seller_id,
        status=case.status,
        verification_level=case.verification_level,
        listing_snapshot=case.listing_snapshot or {},
        analytics_reports=case.analytics_reports or {},
        document_fields=sorted((case.document_refs or {}).keys()),
        decision=case.decision,
        decision_reason=case.decision_reason,
        created_at=case.created_at,
        decided_at=case.decided_at,
    )


@router.get("/cases", response_model=list[ModerationCaseRead])
async def moderation_queue(
    _moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> list[ModerationCaseRead]:
    cases = (await session.scalars(select(ModerationCase).where(
        ModerationCase.status == "pending"
    ).order_by(ModerationCase.created_at.asc()))).all()
    return [_case_read(case) for case in cases]


@router.get("/cases/auto-releases", response_model=list[ModerationCaseRead])
async def auto_release_history(
    _moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> list[ModerationCaseRead]:
    cases = (await session.scalars(select(ModerationCase).where(
        ModerationCase.status == "auto_approved"
    ).order_by(ModerationCase.decided_at.desc()).limit(200))).all()
    return [_case_read(case) for case in cases]


@router.get("/cases/{case_id}", response_model=ModerationCaseRead)
async def get_case(
    case_id: UUID,
    _moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> ModerationCaseRead:
    case = await session.get(ModerationCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Moderation case not found")
    return _case_read(case)


@router.post("/cases/{case_id}/decision", response_model=ModerationCaseRead)
async def decide_case(
    case_id: UUID,
    body: DecisionBody,
    moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> ModerationCaseRead:
    case = await ModerationService(session).decide(case_id, body, moderator["moderator_id"])
    return _case_read(case)


@router.post("/catalog/{listing_id}/remove", response_model=ModerationCaseRead)
async def remove_catalog_listing(
    listing_id: UUID,
    body: CatalogRemovalBody,
    moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> ModerationCaseRead:
    case = await ModerationService(session).remove_from_catalog(
        listing_id, body.reason, moderator["moderator_id"]
    )
    return _case_read(case)


@router.get("/cases/{case_id}/documents/{field}")
async def get_private_document(
    case_id: UUID,
    field: str,
    request: Request,
    _moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    case = await session.get(ModerationCase, case_id)
    relative_path = (case.document_refs or {}).get(field) if case else None
    if not relative_path:
        raise HTTPException(status_code=404, detail="Document not found for this case")
    client: httpx.AsyncClient = request.app.state.http
    upstream_request = client.build_request(
        "GET",
        f"{settings.listing_url}/internal/listings/{case.listing_id}/documents/{field}",
        headers={"X-Moderation-Token": settings.listing_moderation_secret},
    )
    try:
        upstream = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Listing document storage is unavailable") from exc
    if upstream.status_code != status.HTTP_200_OK:
        await upstream.aclose()
        if upstream.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=404, detail="Private document is unavailable")
        raise HTTPException(status_code=502, detail="Listing document storage is unavailable")

    async def document_stream() -> AsyncIterator[bytes]:
        async for chunk in upstream.aiter_bytes():
            yield chunk

    headers = {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    for name in ("content-disposition", "content-length"):
        if name in upstream.headers:
            headers[name] = upstream.headers[name]
    return StreamingResponse(
        document_stream(),
        media_type=upstream.headers.get("content-type", "application/octet-stream"),
        headers=headers,
        background=BackgroundTask(upstream.aclose),
    )


@router.get("/blacklist", response_model=list[BlacklistEntryRead])
async def list_blacklist(
    _moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> list[BlacklistEntry]:
    return list((await session.scalars(select(BlacklistEntry).where(
        BlacklistEntry.is_active.is_(True)
    ).order_by(BlacklistEntry.created_at.desc()))).all())


@router.post("/blacklist", response_model=BlacklistEntryRead, status_code=status.HTTP_201_CREATED)
async def add_to_blacklist(
    body: BlacklistCreate,
    request: Request,
    moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> BlacklistEntry:
    try:
        response = await request.app.state.http.get(
            f"{settings.auth_url}/internal/auth/users/{body.user_id}",
            headers={"X-Moderation-Token": settings.auth_moderation_secret},
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Auth identity lookup is unavailable") from exc
    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=404, detail="User not found")
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=503, detail="Auth identity lookup is unavailable")
    legacy_user_id = int(response.json()["legacy_user_id"])
    return await ModerationService(session).blacklist(body.user_id, body.reason, moderator["moderator_id"], legacy_user_id)


@router.delete("/blacklist/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_blacklist(
    user_id: UUID,
    request: Request,
    moderator: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_db),
) -> None:
    try:
        response = await request.app.state.http.get(
            f"{settings.auth_url}/internal/auth/users/{user_id}",
            headers={"X-Moderation-Token": settings.auth_moderation_secret},
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Auth identity lookup is unavailable") from exc
    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=404, detail="User not found")
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=503, detail="Auth identity lookup is unavailable")
    legacy_user_id = int(response.json()["legacy_user_id"])
    await ModerationService(session).unblacklist(user_id, moderator["moderator_id"], legacy_user_id)

