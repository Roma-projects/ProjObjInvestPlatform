from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BlacklistEntry, ModerationCase, ModerationOutboxEvent
from app.schemas.moderation import DecisionBody

SENSITIVE_DOCUMENT_FIELDS = {"passport_copy_doc"}


class ModerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def decide(self, case_id: UUID, body: DecisionBody, moderator_id: UUID) -> ModerationCase:
        case = await self.session.scalar(select(ModerationCase).where(ModerationCase.id == case_id).with_for_update())
        if case is None:
            raise HTTPException(status_code=404, detail="Moderation case not found")
        if case.status != "pending":
            raise HTTPException(status_code=409, detail="Moderation case is no longer pending")
        banned = await self.session.scalar(select(BlacklistEntry.id).where(
            BlacklistEntry.user_id == case.seller_id, BlacklistEntry.is_active.is_(True)
        ).limit(1))
        if banned:
            case.status = "blocked"
            case.decision = "reject"
            case.decision_reason = "Аккаунт ограничен администрацией платформы."
            case.decision_by = moderator_id
            case.decided_at = datetime.now(timezone.utc)
            self._add_listing_event("moderation.listing.rejected", case, case.decision_reason)
            await self.session.flush()
            return case

        now = datetime.now(timezone.utc)
        case.decision = body.verdict
        case.decision_reason = body.reason
        case.decision_by = moderator_id
        case.decided_at = now
        if body.verdict == "approve":
            case.status = "approved"
            case.verification_level = (
                "deep"
                if SENSITIVE_DOCUMENT_FIELDS.intersection(case.document_refs)
                else "basic"
            )
            self._add_listing_event("moderation.listing.approved", case)
        else:
            case.status = "rejected"
            self._add_listing_event("moderation.listing.rejected", case, body.reason or "Объявление не прошло проверку. Проверьте данные и обратитесь в поддержку.")
        await self.session.flush()
        return case

    async def remove_from_catalog(
        self, listing_id: UUID, reason: str, moderator_id: UUID
    ) -> ModerationCase:
        case = await self.session.scalar(
            select(ModerationCase)
            .where(ModerationCase.listing_id == listing_id)
            .with_for_update()
        )
        if case is None:
            raise HTTPException(status_code=404, detail="Published listing not found")
        if case.status not in {"approved", "auto_approved"}:
            raise HTTPException(status_code=409, detail="Listing is not currently published")

        now = datetime.now(timezone.utc)
        case.status = "removed"
        case.decision = "remove"
        case.decision_reason = reason
        case.decision_by = moderator_id
        case.decided_at = now
        self.session.add(ModerationOutboxEvent(
            routing_key="moderation.listing.removed",
            payload={
                "event": "moderation.listing.removed",
                "listing_id": str(case.listing_id),
                "user_id": str(case.seller_id),
                "user_safe_reason": reason,
                "moderator_id": str(moderator_id),
            },
        ))
        await self.session.flush()
        return case

    async def blacklist(self, user_id: UUID, reason: str, moderator_id: UUID, legacy_user_id: int) -> BlacklistEntry:
        current = await self.session.scalar(select(BlacklistEntry).where(
            BlacklistEntry.user_id == user_id, BlacklistEntry.is_active.is_(True)
        ).with_for_update())
        if current:
            return current
        entry = BlacklistEntry(user_id=user_id, reason=reason, banned_by=moderator_id, is_active=True)
        self.session.add(entry)
        await self.session.flush()
        pending_cases = (await self.session.scalars(select(ModerationCase).where(
            ModerationCase.seller_id == user_id, ModerationCase.status == "pending"
        ).with_for_update())).all()
        for case in pending_cases:
            case.status = "blocked"
            case.decision = "reject"
            case.decision_reason = "Аккаунт добавлен в чёрный список."
            case.decision_by = moderator_id
            case.decided_at = datetime.now(timezone.utc)
        self.session.add(ModerationOutboxEvent(routing_key="moderation.user.blacklisted", payload={
            "event": "moderation.user.blacklisted", "user_id": str(user_id),
            "legacy_user_id": legacy_user_id, "reason": reason, "moderator_id": str(moderator_id),
        }))
        return entry

    async def unblacklist(self, user_id: UUID, moderator_id: UUID, legacy_user_id: int) -> BlacklistEntry:
        entry = await self.session.scalar(select(BlacklistEntry).where(
            BlacklistEntry.user_id == user_id, BlacklistEntry.is_active.is_(True)
        ).with_for_update())
        if entry is None:
            raise HTTPException(status_code=404, detail="User is not on the blacklist")
        entry.is_active = False
        entry.released_at = datetime.now(timezone.utc)
        entry.released_by = moderator_id
        self.session.add(ModerationOutboxEvent(routing_key="moderation.user.unblocked", payload={
            "event": "moderation.user.unblocked", "user_id": str(user_id),
            "legacy_user_id": legacy_user_id, "moderator_id": str(moderator_id),
        }))
        await self.session.flush()
        return entry

    def _add_listing_event(self, routing_key: str, case: ModerationCase, reason: str | None = None) -> None:
        payload = {
            "event": routing_key,
            "listing_id": str(case.listing_id),
            "user_id": str(case.seller_id),
            "verification_level": case.verification_level,
        }
        if reason:
            payload["user_safe_reason"] = reason
        self.session.add(ModerationOutboxEvent(routing_key=routing_key, payload=payload))

