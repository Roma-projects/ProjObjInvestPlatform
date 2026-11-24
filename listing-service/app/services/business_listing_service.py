"""Сохранение бизнес-объявлений, приватных документов и событий жизненного цикла."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import aiofiles
from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.business_listing import BlockedUser, BusinessListing
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
        "seller_id": str(row.user_id),
        "seller_name": row.seller_name,
        "business_name": row.business_name,
        "short_description": row.short_description,
        "full_description": row.full_description,
        "business_type": row.business_type,
        "sale_price": float(row.sale_price) if row.sale_price is not None else None,
        "stock_included": row.stock_included,
        "stock_value": float(row.stock_value) if row.stock_value is not None else None,
        "area_sqm": row.area_sqm,
        "floor_number": row.floor_number,
        "has_separate_entrance": row.has_separate_entrance,
        "parking_spaces": row.parking_spaces,
        "ceiling_height": row.ceiling_height,
        "equipment_list": row.equipment_list or [],
        "staff_count": row.staff_count,
        "staff_details": row.staff_details or [],
        "working_hours": row.working_hours,
        "business_age_months": row.business_age_months,
        "has_licenses": row.has_licenses,
        "has_contracts": row.has_contracts,
        "sale_reason": row.sale_reason,
        "stay_as_consultant_months": row.stay_as_consultant_months,
        "monthly_financials": row.monthly_financials or [],
        "average_check": float(row.average_check) if row.average_check is not None else None,
        "monthly_orders": row.monthly_orders,
        "monthly_clients_unique": row.monthly_clients_unique,
        "cost_structure": row.cost_structure or [],
        "seasonality_months": row.seasonality_months or [],
        "peak_hours": row.peak_hours or [],
        "supplier_contracts": row.supplier_contracts,
        "supplier_details": row.supplier_details,
        "debts_receivable": float(row.debts_receivable) if row.debts_receivable is not None else None,
        "debts_payable": float(row.debts_payable) if row.debts_payable is not None else None,
        "legal_claims": row.legal_claims,
        "legal_claims_details": row.legal_claims_details,
        "equipment_lease": row.equipment_lease,
        "monthly_loan_payments": float(row.monthly_loan_payments) if row.monthly_loan_payments is not None else None,
        "customer_base_size": row.customer_base_size,
        "repeat_customer_rate": row.repeat_customer_rate,
        "avg_monthly_revenue": avg_revenue,
        "location": {"country": row.country, "city": row.city, "street": row.street, "house": row.house},
        "photos": [*files.get("photos", [])],
        "main_photo": files.get("main_photo"),
        "floor_plan_image": files.get("floor_plan_image"),
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
        if await self.session.get(BlockedUser, user_id):
            raise HTTPException(status_code=403, detail="Account is blocked")
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
        await self.session.refresh(row, attribute_names=["id", "status", "verification_status", "created_at", "updated_at"])
        return to_response(row)

    async def upload_file(self, user_id: UUID, listing_id: UUID, field: str, upload: UploadFile) -> dict[str, Any]:
        if await self.session.get(BlockedUser, user_id):
            raise HTTPException(status_code=403, detail="Account is blocked")
        row = await self.get(user_id, listing_id)
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Files can only be uploaded to a draft")
        if field not in PUBLIC_FIELDS | PRIVATE_FIELDS:
            raise HTTPException(status_code=422, detail="Unknown file field")
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in MIME_BY_SUFFIX or upload.content_type not in MIME_BY_SUFFIX[suffix]:
            raise HTTPException(status_code=415, detail="Unsupported file type")
        is_public = field in PUBLIC_FIELDS
        if field == "photos" and len((row.files or {}).get("photos", [])) >= 10:
            raise HTTPException(status_code=422, detail="Maximum 10 additional photos are allowed")
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
        replaced_public_path = None
        if is_public:
            public_path = f"/public/uploads/{relative}"
            files = dict(row.files or {})
            if field == "photos":
                # JSONB columns are tracked as values, not mutable nested structures.
                # Assign a fresh list so SQLAlchemy detects each appended upload.
                files["photos"] = [*(files.get("photos") or []), public_path]
            else:
                replaced_public_path = files.get(field)
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
        await self.session.refresh(row, attribute_names=["files", "documents", "video_url"])
        result = {
            "field": field,
            "path": result_path if is_public else None,
            "size_bytes": size,
            "visibility": "public" if is_public else "private",
        }
        await self.session.commit()
        if isinstance(replaced_public_path, str):
            prefix = f"/public/uploads/listings/{listing_id}/"
            if replaced_public_path.startswith(prefix):
                previous_path = (Path(settings.public_upload_dir) / replaced_public_path.removeprefix("/public/uploads/")).resolve()
                if previous_path.parent == (Path(settings.public_upload_dir) / "listings" / str(listing_id)).resolve():
                    previous_path.unlink(missing_ok=True)
        return result

    async def replace_photo(self, user_id: UUID, listing_id: UUID, index: int, upload: UploadFile) -> dict[str, Any]:
        if await self.session.get(BlockedUser, user_id):
            raise HTTPException(status_code=403, detail="Account is blocked")
        row = await self.get(user_id, listing_id)
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Photos can only be replaced on a draft")
        files = dict(row.files or {})
        photos = list(files.get("photos") or [])
        if index < 0 or index >= len(photos):
            raise HTTPException(status_code=404, detail="Photo not found")

        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in MIME_BY_SUFFIX or upload.content_type not in MIME_BY_SUFFIX[suffix] or not upload.content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="Unsupported image type")

        root = Path(settings.public_upload_dir)
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

        old_path = photos[index]
        photos[index] = f"/public/uploads/listings/{listing_id}/{stored_name}"
        files["photos"] = photos
        row.files = files
        try:
            await self.session.flush()
            await self.session.commit()
        except Exception:
            target_path.unlink(missing_ok=True)
            raise

        prefix = f"/public/uploads/listings/{listing_id}/"
        if isinstance(old_path, str) and old_path.startswith(prefix):
            old_file = (root / old_path.removeprefix("/public/uploads/")).resolve()
            if old_file.parent == target_dir.resolve():
                old_file.unlink(missing_ok=True)
        return {"field": "photos", "index": index, "path": photos[index], "size_bytes": size, "visibility": "public"}

    async def delete_draft(self, user_id: UUID, listing_id: UUID) -> None:
        row = await self.get(user_id, listing_id)
        if row.status != "draft":
            raise HTTPException(status_code=409, detail="Only draft listings can be deleted")

        for upload_root in (settings.public_upload_dir, settings.private_upload_dir):
            root = Path(upload_root).resolve()
            listing_dir = (root / "listings" / str(listing_id)).resolve()
            if listing_dir.parent == root / "listings" and listing_dir.is_dir():
                shutil.rmtree(listing_dir)

        await self.session.delete(row)
        await self.session.flush()

    async def submit(self, user_id: UUID, listing_id: UUID) -> BusinessListingResponse:
        row = await self.get(user_id, listing_id)
        if await self.session.get(BlockedUser, user_id):
            raise HTTPException(status_code=403, detail="Account is blocked")
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
        row.status = "processing"
        await self.session.flush()
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
        # ORM numeric columns are Decimal; encode before storing the event in JSONB.
        self.session.add(OutboxEvent(routing_key="listing.creation.started", payload=jsonable_encoder(payload)))
        await self.session.flush()
        # updated_at is generated by PostgreSQL (onupdate=func.now()) and may
        # be expired after flush. Load response fields asynchronously so
        # to_response() cannot trigger implicit IO outside greenlet context.
        await self.session.refresh(
            row,
            attribute_names=["id", "status", "verification_status", "created_at", "updated_at"],
        )
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
