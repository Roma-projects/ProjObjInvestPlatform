"""Выполняет осторожные HTTP-запросы к четырём открытым источникам из ТЗ."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.extractors import extract_file
from app.storage import LocalStorage, MongoStorage

logger = logging.getLogger(__name__)
settings = get_settings()
_LAST_REQUEST: dict[str, float] = {}
_FAILURES: dict[str, tuple[int, float]] = {}
_USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
)


class SourceUnavailable(RuntimeError):
    """Сигнализирует, что источник не отвечает или требует недоступной проверки."""


class RegistryParser:
    """Скачивает доступную страницу реестра, сохраняет её и пробует разобрать ответ."""

    source = ""
    url = ""

    async def run(self, *, inn: str, ogrnip: str | None, fio: str,
                  storage: LocalStorage, mongo: MongoStorage) -> dict[str, Any]:
        failures, disabled_until = _FAILURES.get(self.source, (0, 0.0))
        if time.monotonic() < disabled_until:
            raise SourceUnavailable("Circuit breaker is open")
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                wait = max(0.0, 2.0 - (time.monotonic() - _LAST_REQUEST.get(self.source, 0.0)))
                if wait:
                    await asyncio.sleep(wait)
                headers = {"User-Agent": _USER_AGENTS[attempt % len(_USER_AGENTS)]}
                async with httpx.AsyncClient(timeout=settings.request_timeout_seconds,
                                             follow_redirects=True, headers=headers) as client:
                    response = await self.fetch(client, inn, ogrnip, fio)
                _LAST_REQUEST[self.source] = time.monotonic()
                response.raise_for_status()
                _FAILURES[self.source] = (0, 0.0)
                content_type = response.headers.get("content-type", "application/octet-stream").split(";")[0]
                files, extracts = await self._save_response(response, storage, mongo, storage.directory.name)
                return {"extract": self._normalize(" ".join(item.get("text", "") for item in extracts)),
                        "files": [str(path) for path in files], "original_url": str(response.url),
                        "content_type": content_type}
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(3**attempt)
        count, _ = _FAILURES.get(self.source, (0, 0.0))
        count += 1
        _FAILURES[self.source] = (count, time.monotonic() + 300 if count >= 5 else 0.0)
        raise SourceUnavailable(f"{self.source} failed: {type(last_error).__name__}") from last_error

    async def fetch(self, client: httpx.AsyncClient, inn: str, ogrnip: str | None, fio: str) -> httpx.Response:
        return await client.get(self.url, params={"query": inn, "inn": inn})

    async def _save_response(self, response: httpx.Response, storage: LocalStorage,
                             mongo: MongoStorage, listing_id: str) -> tuple[list[Path], list[dict[str, Any]]]:
        paths: list[Path] = []
        extracts: list[dict[str, Any]] = []
        content = response.content
        if content.startswith(b"PK"):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                for info in archive.infolist():
                    name = Path(info.filename).name
                    if not name or info.is_dir():
                        continue
                    path = storage.save(name, archive.read(info))
                    paths.append(path)
                    extracts.append(extract_file(path))
                    await mongo.record_file(listing_id, self.source, path, str(response.url), "application/zip")
            return paths, extracts
        suffix = ".pdf" if "pdf" in response.headers.get("content-type", "") else ".html"
        path = storage.save(f"{self.source}{suffix}", content)
        paths.append(path)
        extracts.append(extract_file(path))
        await mongo.record_file(listing_id, self.source, path, str(response.url), response.headers.get("content-type", "application/octet-stream"))
        return paths, extracts

    def _normalize(self, text: str) -> dict[str, Any]:
        """Извлекает только известные подписи; отсутствие данных остаётся null."""
        clean = re.sub(r"\s+", " ", text).strip()
        return {"fio": None, "ogrnip": None, "registration_date": None, "okved": [],
                "status": None, "region": None, "tax_system": None, "employee_count": None,
                "annual_revenue": None, "risk_factors": [], "bankruptcy_proceedings": False,
                "arbitration_cases": [], "source_text_excerpt": clean[:2000] or None}


class EgrulParser(RegistryParser):
    source, url = "egrul", settings.egrul_url

    async def fetch(self, client: httpx.AsyncClient, inn: str, ogrnip: str | None, fio: str) -> httpx.Response:
        """Запускает задание ФНС и ждёт ZIP-выписку, не опрашивая другие сервисы."""
        start = await client.post(self.url, data={"query": inn})
        start.raise_for_status()
        try:
            task = start.json()
            task_id = task.get("t") or task.get("taskId") or task.get("id")
        except ValueError:
            task_id = None
        if not task_id:
            raise SourceUnavailable("EGRUL did not return a task identifier")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            await asyncio.sleep(2)
            status_response = await client.get(f"{self.url.rstrip('/')}/search-result/{task_id}")
            status_response.raise_for_status()
            try:
                status_data = status_response.json()
            except ValueError:
                status_data = {}
            records = status_data.get("rows") or status_data.get("items") or []
            if records:
                record_id = records[0].get("t") or records[0].get("id") or task_id
                download = await client.get(f"{self.url.rstrip('/')}/vyp-download/{record_id}")
                download.raise_for_status()
                return download
        raise SourceUnavailable("EGRUL result timed out")


class PbParser(RegistryParser):
    source, url = "pb", settings.pb_url


class FedresursParser(RegistryParser):
    source, url = "fedresurs", settings.fedresurs_url


class KadParser(RegistryParser):
    source, url = "kad", settings.kad_url
