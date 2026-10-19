"""Вызывает Qwen через OpenAI-compatible endpoint и строго фильтрует выходные поля."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.analysis import detect_red_flags, fallback_report
from app.config import get_settings

settings = get_settings()

_SYSTEM_PROMPT = """Ты проверяешь объявление о продаже готового бизнеса. Выполняй только четыре задачи: red flags, краткая сводка числовых метрик, модерация фотографий и два отчёта (модератору и продавцу). Не создавай рекламные тексты. Не включай ИНН, ОГРНИП, документы, контакты, детальные месячные расходы, долги, претензии или moderator_report в user_analytics. При сомнении требуй ручную модерацию. Возвращай JSON строго по переданной JSON Schema."""

_SCHEMA = {
    "name": "business_listing_ai_report",
    "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False,
        "required": ["moderation_status", "moderation_reasons", "content_moderation",
                     "price_assessment", "forecast", "moderator_report", "user_analytics"],
        "properties": {
            "moderation_status": {"type": "string", "enum": ["auto_ok", "requires_moderation"]},
            "moderation_reasons": {"type": "array", "items": {"type": "string"}},
            "content_moderation": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "price_assessment": {"type": "object", "additionalProperties": True},
            "forecast": {"type": "object", "additionalProperties": True},
            "moderator_report": {"type": "object", "additionalProperties": True},
            "user_analytics": {"type": "object", "additionalProperties": True},
        },
    },
}

_SAFE_ANALYTICS = {
    "average_monthly_revenue", "average_monthly_net_profit", "payback_months",
    "revenue_trend", "fair_range_min", "fair_range_max", "forecast_direction",
}


class QwenAnalyzer:
    """Uses Qwen if configured; otherwise returns a conservative report requiring review."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=settings.model_timeout_seconds)

    async def close(self) -> None:
        await self.client.aclose()

    def endpoint_host(self) -> str:
        return urlparse(settings.qwen_base_url).hostname or "not-configured"

    async def analyze(self, data: dict[str, Any], registry: dict[str, Any] | None) -> dict[str, Any]:
        base = fallback_report(data, registry)
        if not settings.qwen_base_url:
            return base
        content: list[dict[str, Any]] = [{
            "type": "text",
            "text": json.dumps({"data_for_analytics": data, "registry_extract": registry or {}}, ensure_ascii=False),
        }]
        content.extend(self._image_content(data))
        headers = {"Content-Type": "application/json"}
        if settings.qwen_api_key:
            headers["Authorization"] = f"Bearer {settings.qwen_api_key}"
        response = await self.client.post(
            f"{settings.qwen_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": settings.qwen_model,
                "temperature": 0.1,
                "messages": [{"role": "system", "content": _SYSTEM_PROMPT}, {"role": "user", "content": content}],
                "response_format": {"type": "json_schema", "json_schema": _SCHEMA},
            },
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        generated = json.loads(raw)
        base.update(generated)
        base["red_flags"] = detect_red_flags(data, registry)
        base["red_flag_score"] = min(100, sum({"critical": 40, "high": 20, "medium": 10}.get(flag["severity"], 0)
                                                  for flag in base["red_flags"]))
        if any(flag["severity"] == "critical" for flag in base["red_flags"]):
            base["moderation_status"] = "requires_moderation"
        if not isinstance(base.get("user_analytics"), dict):
            base["user_analytics"] = {}
        base["user_analytics"] = {key: value for key, value in base["user_analytics"].items()
                                  if key in _SAFE_ANALYTICS}
        return base

    def _image_content(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Reads only images from public_uploads; private paperwork is never opened."""
        media = data.get("media_files") or {}
        paths: list[str] = []
        for value in [media.get("main_photo"), *(media.get("photos") or []), media.get("floor_plan_image")]:
            if value:
                paths.append(str(value))
        root = Path(settings.public_upload_dir).resolve()
        result: list[dict[str, Any]] = []
        for uri in paths[:5]:
            relative = uri.removeprefix("/public/uploads/").lstrip("/")
            path = (root / relative).resolve()
            if root not in path.parents or not path.is_file():
                continue
            suffix = path.suffix.lower()
            mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffix)
            if not mime:
                continue
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            result.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
        return result
