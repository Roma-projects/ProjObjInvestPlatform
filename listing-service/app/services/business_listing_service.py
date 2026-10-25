"""Сохранение бизнес-объявлений, приватных документов и событий жизненного цикла."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.business_listing import BusinessListing
from app.models.outbox import OutboxEvent
from app.rabbitmq.publisher import publisher
from app.schemas.business_listing import BusinessListingDraft, BusinessListingResponse

logger = logging.getLogger(__name__)
settings = get_settings()

PUBLIC_FIELDS = {"main_photo", "photos", "floor_plan_image", "video"}
PRIVATE_FIELDS = {
    "evacuation_plan_doc", "fire_declaration_doc", "fire_service_contract_doc",
    "san_epid_conclusion", "tax_certificate_doc", "income_statement_doc",
    "lease_agreement_doc", "ownership_doc", "passport_copy_doc",
}
SENSITIVE_MODERATION_DOCUMENTS = {"passport_copy_doc", "tax_certificate_doc", "income_statement_doc"}
MIME_BY_SUFFIX = {
    ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"}, ".png": {"image/png"},
    ".webp": {"image/webp"}, ".pdf": {"application/pdf"},
    ".mp4": {"video/mp4"}, ".mov": {"video/quicktime"},
}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def to_response(row: BusinessListing) -> BusinessListingResponse:
    return BusinessListingResponse(
        id=row.id,
        status=row.status,
        verification_status=row.verification_status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _field_values(body: BusinessListingDraft) -> dict[str, Any]:
    return body.model_dump(mode="json", exclude_unset=True)


def _data_for_analytics(row: BusinessListing) -> dict[str, Any]:
    data = {
        key: getattr(row, key)
        for key in (
            "business_type", "business_name", "short_description", "full_description", "sale_price",
            "stock_included", "stock_value", "property_type", "deal_composition", "transfer_method",
            "property_condition", "area_sqm", "equipment_list", "staff_count", "staff_details",
            "business_age_months", "has_licenses", "has_contracts", "sale_reason", "monthly_financials",
            "average_check", "monthly_orders", "monthly_clients_unique", "repeat_customer_rate",
            "customer_base_size", "cost_structure", "seasonality_months", "peak_hours", "supplier_contracts",
            "supplier_details", "debts_receivable", "debts_payable", "legal_claims", "legal_claims_details",
            "equipment_lease", "monthly_loan_payments", "seller_name", "seller_status", "seller_inn", "seller_ogrnip", "tax_system",
        )
    }
    data["staff_details"] = data["staff_details"] or []
    data["equipment_list"] = data["equipment_list"] or []
    data["monthly_financials"] = data["monthly_financials"] or []
    data["has_documents"] = {key: key in (row.documents or {}) for key in PRIVATE_FIELDS}
    data["media_files"] = {
        key: value for key, value in (row.files or {}).items()
        if key in {"main_photo", "photos", "video", "floor_plan_image"}
    }
    data["country"] = row.country
    data["city"] = row.city
    data["street"] = row.street
    return data


def _valid_ip_inn(inn: str | None) -> bool:
    """Проверяет контрольные цифры ИНН ИП по алгоритму ФНС (12 цифр)."""
    if not inn or len(inn) != 12 or not inn.isdigit():
        return False
    digits = [int(value) for value in inn]
    first_weights = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    second_weights = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    first_check = sum(digit * weight for digit, weight in zip(digits[:10], first_weights)) % 11 % 10
    second_check = sum(digit * weight for digit, weight in zip(digits[:11], second_weights)) % 11 % 10
    return digits[10] == first_check and digits[11] == second_check


def _public_data(row: BusinessListing) -> dict[str, Any]:
    """Allow-list only fields safe for Search+Catalog; private data is never serialized."""
    finances = row.monthly_financials or []
    avg_revenue = None
    if finances:
        avg_revenue = sum(float(item.get("revenue", 0)) for item in finances) / len(finances)
    files = row.files or {}
    ai_report = (row.analytics_results or {}).get("ai_report", {})
    return {
        "business_name": row.business_name,
        "short_description": row.short_description,
        "business_type": row.business_type,
        "sale_price": float(row.sale_price) if row.sale_price is not None else None,
        "avg_monthly_revenue": avg_revenue,
        "location": {"country": row.country, "city": row.city, "street": row.street},
        "photos": [*files.get("photos", [])],
        "main_photo": files.get("main_photo"),
        "video": row.video_url or files.get("video"),
        "deal_composition": row.deal_composition,
        "property_type": row.property_type,
        "property_condition": row.property_condition,
        "transfer_method": row.transfer_method,
        "revenue_trend": row.revenue_trend,
        "verification_status": row.verification_status,
        "user_analytics": ai_report.get("user_analytics", {}),
    }


class BusinessListingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_draft(self, user_id: UUID, body: BusinessListingDraft) -> BusinessListingResponse:
        row = BusinessListing(user_id=user_id, **_field_values(body))
        self.session.add(row)
        await self.session.flush()
        return to_response(row)

    async def get(self, user_id: UUID, listing_id: UUID) -> BusinessListing:
        row = await self.session.scalar(
            select(BusinessListing).where(BusinessListing.id == listing_id, BusinessListing.user_id == user_id)
        )
        if not row:
            raise HTTPException(status_code=404, detail="Listing not found")
        return row

    async def update_draft(self, user_id: UUID, listing_id: UUID, body: BusinessListingDraft) -> BusinessListingResponse:
        row = await self.get(user_id, listing_id)
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Only draft listings can be edited")
        for key, value in _field_values(body).items():
            setattr(row, key, value)
        await self.session.flush()
        return to_response(row)

    async def upload_file(self, user_id: UUID, listing_id: UUID, field: str, upload: UploadFile) -> dict[str, Any]:
        row = await self.get(user_id, listing_id)
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Files can only be uploaded to a draft")
        if field not in PUBLIC_FIELDS | PRIVATE_FIELDS:
            raise HTTPException(status_code=422, detail="Unknown file field")
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in MIME_BY_SUFFIX or upload.content_type not in MIME_BY_SUFFIX[suffix]:
            raise HTTPException(status_code=415, detail="Unsupported file type")
        is_public = field in PUBLIC_FIELDS
        root = Path(settings.public_upload_dir if is_public else settings.private_upload_dir)
        target_dir = root / "listings" / str(listing_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        target_path = target_dir / stored_name
        size = 0
        try:
            async with aiofiles.open(target_path, "wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail="Maximum file size is 100 MB")
                    await destination.write(chunk)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        relative = f"listings/{listing_id}/{stored_name}"
        if is_public:
            public_path = f"/public/uploads/{relative}"
            files = dict(row.files or {})
            if field == "photos":
                files.setdefault("photos", []).append(public_path)
            else:
                files[field] = public_path
                if field == "video":
                    row.video_url = public_path
            row.files = files
            result_path = public_path
        else:
            documents = dict(row.documents or {})
            documents[field] = relative
            row.documents = documents
            result_path = relative
        await self.session.flush()
        return {"field": field, "path": result_path, "size_bytes": size, "visibility": "public" if is_public else "private"}

    async def submit(self, user_id: UUID, listing_id: UUID) -> BusinessListingResponse:
        row = await self.get(user_id, listing_id)
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Listing was already submitted")
        required = {
            "business_type": row.business_type,
            "property_type": row.property_type,
            "transfer_method": row.transfer_method,
            "deal_composition": row.deal_composition,
            "business_name": row.business_name,
            "short_description": row.short_description,
            "sale_price": row.sale_price,
            "country": row.country,
            "city": row.city,
            "seller_status": row.seller_status,
        }
        missing = [field for field, value in required.items() if value is None or value == ""]
        files = row.files or {}
        if not files.get("main_photo"):
            missing.append("main_photo")
        if len(files.get("photos", [])) < 5:
            missing.append("photos (minimum 5)")
        if missing:
            raise HTTPException(status_code=422, detail={"missing_fields": missing})

        correlation_id = str(uuid.uuid4())
        critical_documents_attached = bool(SENSITIVE_MODERATION_DOCUMENTS.intersection(row.documents or {}))
        if critical_documents_attached:
            row.status = "on_moderation"
            row.verification_status = "deep"
        else:
            row.status = "processing"
        payload = {
            "event": "listing.creation.started",
            "correlation_id": correlation_id,
            "listing_id": str(row.id),
            "user_id": str(row.user_id),
            "data_for_analytics": _data_for_analytics(row),
        }
        trigger_parsers = row.seller_status == "ip" and bool(row.seller_name) and _valid_ip_inn(row.seller_inn)
        if not trigger_parsers:
            payload["data_for_analytics"]["registry_check"] = (
                "invalid_inn" if row.seller_status == "ip" and row.seller_inn else "skipped"
            )
        else:
            payload["data_for_analytics"]["registry_check"] = "awaiting"
        if trigger_parsers:
            # Publish the parser job first so reply_to exists before Parsers can finish.
            self.session.add(OutboxEvent(routing_key="parsers.request.registry", payload={
                "event": "parsers.request.registry",
                "correlation_id": correlation_id,
                "reply_to": f"ai.reply.{correlation_id}",
                "listing_id": str(row.id),
                "fio": row.seller_name,
                "inn": row.seller_inn,
                "status": row.seller_status,
                "ogrnip": row.seller_ogrnip,
                "sources": ["egrul", "pb", "fedresurs", "kad"],
                "ttl_seconds": 120,
            }))
        self.session.add(OutboxEvent(routing_key="listing.creation.started", payload=payload))
        if critical_documents_attached:
            self.session.add(OutboxEvent(
                routing_key="listing.on_moderation",
                payload={"event": "listing.on_moderation", "listing_id": str(row.id), "user_id": str(row.user_id), "verification_status": "deep"},
            ))
        await self.session.flush()
        return to_response(row)

    async def moderate(self, listing_id: UUID, verdict: str, user_safe_reason: str | None) -> BusinessListingResponse:
        """Applies the final human decision and emits only the corresponding public event."""
        row = await self.session.scalar(
            select(BusinessListing).where(BusinessListing.id == listing_id).with_for_update()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Listing not found")
        if row.status != "on_moderation":
            raise HTTPException(status_code=409, detail="Listing is not waiting for moderation")
        has_sensitive_docs = bool(SENSITIVE_MODERATION_DOCUMENTS.intersection(row.documents or {}))
        if verdict == "approve":
            row.status = "published"
            row.verification_status = "deep" if has_sensitive_docs else "basic"
            self.session.add(OutboxEvent(routing_key="listing.creation.completed", payload={
                "event": "listing.creation.completed", "listing_id": str(row.id),
                "user_id": str(row.user_id), "public_data": _public_data(row),
            }))
        else:
            row.status = "rejected"
            self.session.add(OutboxEvent(routing_key="listing.rejected", payload={
                "event": "listing.rejected", "listing_id": str(row.id),
                "user_id": str(row.user_id), "user_safe_reason": user_safe_reason or "Объявление не прошло проверку. Проверьте данные и обратитесь в поддержку.",
            }))
        await self.session.flush()
        return to_response(row)


async def run_outbox_dispatcher(stop: asyncio.Event) -> None:
    """Publish committed events; a stable event ID lets consumers safely deduplicate retries."""
    while not stop.is_set():
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.now(timezone.utc)
                pending = (await session.scalars(
                    select(OutboxEvent)
                    .where(OutboxEvent.state == "pending", OutboxEvent.available_at <= now)
                    .order_by(OutboxEvent.created_at)
                    .limit(25)
                    .with_for_update(skip_locked=True)
                )).all()
                for item in pending:
                    item.payload.setdefault("event_id", str(item.id))
                    try:
                        if not await publisher.publish_business_event(item.routing_key, item.payload):
                            raise RuntimeError("RabbitMQ is unavailable")
                        item.state = "published"
                        item.published_at = now
                        item.last_error = None
                    except Exception as exc:
                        item.attempts += 1
                        item.last_error = str(exc)[:500]
                        if item.attempts >= 12:
                            item.state = "dead"
                        else:
                            item.available_at = now + timedelta(seconds=min(300, 2 ** item.attempts))
                await session.commit()
        except Exception:
            logger.exception("Outbox dispatch cycle failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except TimeoutError:
            pass
