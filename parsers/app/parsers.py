"""Выполняет осторожные HTTP-запросы к четырём открытым источникам из ТЗ."""

from __future__ import annotations

import asyncio
import io
import logging
import re
import time
import zipfile
from abc import ABC, abstractmethod
from itertools import cycle
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.extractors import extract_file
from app.storage import LocalStorage, MongoStorage

logger = logging.getLogger(__name__)
settings = get_settings()
_LAST_REQUEST: dict[str, float] = {}
_SOURCE_LOCKS: dict[str, asyncio.Lock] = {}
_FAILURES: dict[str, tuple[int, float]] = {}
_USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
)
_USER_AGENT_ROTATION = cycle(_USER_AGENTS)


def _next_user_agent() -> str:
    """Возвращает следующий User-Agent из небольшого набора обычных браузеров."""
    return next(_USER_AGENT_ROTATION)


class SourceUnavailable(RuntimeError):
    """Сигнализирует, что источник не отвечает или требует недоступной проверки."""


class RegistryParser(ABC):
    """Получает ответ реестра; сохраняет документы, а HTML использует только для текста."""

    source = ""
    url = ""

    async def run(self, *, inn: str, ogrnip: str | None, fio: str,
                  storage: LocalStorage, mongo: MongoStorage) -> dict[str, Any]:
        _, disabled_until = _FAILURES.get(self.source, (0, 0.0))
        if time.monotonic() < disabled_until:
            raise SourceUnavailable("Circuit breaker is open")
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                # Резервируем время запроса под блокировкой, чтобы параллельные задачи
                # не отправляли запросы к одному источнику одновременно.
                source_lock = _SOURCE_LOCKS.setdefault(self.source, asyncio.Lock())
                async with source_lock:
                    wait = max(0.0, 2.0 - (time.monotonic() - _LAST_REQUEST.get(self.source, 0.0)))
                    if wait:
                        await asyncio.sleep(wait)
                    _LAST_REQUEST[self.source] = time.monotonic()
                headers = {"User-Agent": _next_user_agent()}
                async with httpx.AsyncClient(timeout=settings.request_timeout_seconds,
                                             follow_redirects=True, headers=headers) as client:
                    response = await self.fetch(client, inn, ogrnip, fio)
                response.raise_for_status()
                _FAILURES[self.source] = (0, 0.0)
                files, extracts = await self._save_response(response, storage, mongo, storage.directory.name)
                source_text = re.sub(
                    r"\s+", " ", " ".join(item.get("text", "") for item in extracts)
                ).strip()
                return {"extract": {"source_text_excerpt": source_text[:2000] or None},
                        "files": [str(path) for path in files]}
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Registry source %s attempt %s/3 failed (%s): %s",
                    self.source, attempt + 1, type(exc).__name__, _safe_error(exc),
                )
                # 401/403 и другие постоянные 4xx нельзя исправить повтором;
                # прекращаем запросы сразу и не нагружаем закрытый источник.
                if (isinstance(exc, httpx.HTTPStatusError)
                        and 400 <= exc.response.status_code < 500
                        and exc.response.status_code not in {408, 429}):
                    break
                if attempt < 2:
                    await asyncio.sleep(3**attempt)
        count, _ = _FAILURES.get(self.source, (0, 0.0))
        count += 1
        _FAILURES[self.source] = (count, time.monotonic() + 300 if count >= 5 else 0.0)
        detail = _safe_error(last_error) if last_error else "unknown error"
        raise SourceUnavailable(
            f"{self.source} failed after {attempt + 1} attempt(s) "
            f"({type(last_error).__name__}): {detail}"
        ) from last_error

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient, inn: str, ogrnip: str | None, fio: str) -> httpx.Response:
        """Выполняет поиск на конкретном сайте и возвращает HTTP-ответ."""
        raise NotImplementedError("Each registry parser must implement fetch")

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
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" in content_type or content.lstrip().lower().startswith((b"<!doctype html", b"<html")):
            # Страница поиска — не документ реестра: читаем её текст, но не сохраняем HTML-файл.
            text = BeautifulSoup(content, "lxml").get_text(" ", strip=True)
            return [], [{"text": text}]
        if "pdf" in content_type or content.startswith(b"%PDF-"):
            suffix = ".pdf"
        elif "xml" in content_type or content.lstrip().startswith(b"<?xml"):
            suffix = ".xml"
        else:
            raise SourceUnavailable("Registry response is not a downloadable document")
        path = storage.save(f"{self.source}{suffix}", content)
        paths.append(path)
        extracts.append(extract_file(path))
        await mongo.record_file(listing_id, self.source, path, str(response.url), response.headers.get("content-type", "application/octet-stream"))
        return paths, extracts

    async def _download_fns_pdf(self, inn: str, source: str) -> httpx.Response:
        """Ищет ИНН на сайте ФНС и возвращает загруженный браузером PDF-файл."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise SourceUnavailable("Install the Playwright dependency to download registry PDFs") from exc

        if source == "egrul":
            # Корень ФНС делает redirect, который иногда зависает в Playwright.
            start_url = urljoin(settings.egrul_url.rstrip("/") + "/", "index.html")
        else:
            # На главной PB radio-переключатель и поле ИП скрыты до выполнения UI-скриптов.
            # Специализированная форма сразу показывает корректный queryIp.
            start_url = urljoin(settings.pb_url.rstrip("/") + "/", "search.html#search-ip")
        stage = "browser launch"
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, chromium_sandbox=True)
            try:
                context = await browser.new_context(
                    accept_downloads=True,
                )
                page = await context.new_page()
                page.set_default_timeout(settings.request_timeout_seconds * 1000)
                # Ждём готовый DOM: поля поиска появляются после разбора HTML.
                # Используем прямые страницы index/search, чтобы не ждать redirect.
                stage = "page navigation"
                await page.goto(start_url, wait_until="domcontentloaded", timeout=45_000)

                if source == "egrul":
                    stage = "EGRUL search form"
                    await page.locator("#query").wait_for(state="visible")
                    await page.locator("#query").fill(inn)
                    await page.locator("#btnSearch").click()
                    stage = "EGRUL result card"
                    record = page.locator(".res-line").filter(has_text=inn).first
                    await record.wait_for(state="visible")
                    button = record.locator("button.op-excerpt")
                else:
                    stage = "PB search form"
                    await page.locator("#queryIp").wait_for(state="visible")
                    await page.locator("#queryIp").fill(inn)
                    await page.get_by_role("button", name="Искать").click()
                    # В актуальной верстке результат находится в .pb-card--clickable,
                    # а не в старом классе .resultip; ссылка на PDF есть в карточке сразу.
                    stage = "PB result card"
                    record = page.locator(".pb-card--clickable").filter(has_text=inn).first
                    await record.wait_for(state="visible")
                    await record.click()
                    stage = "PB PDF link"
                    button = page.locator('a.lnk-egrl[title="Скачать выписку из ЕГРИП"]').last
                    await button.wait_for(state="visible")

                stage = "PDF download"
                async with page.expect_download(timeout=settings.request_timeout_seconds * 1000) as pending:
                    await button.click()
                download = await pending.value
                file_path = await download.path()
                if not file_path:
                    raise SourceUnavailable("Registry PDF download did not produce a local file")
                content = await asyncio.to_thread(Path(file_path).read_bytes)
                if not content.startswith(b"%PDF-"):
                    raise SourceUnavailable("Registry download was not a PDF document")
                return httpx.Response(
                    200,
                    headers={"content-type": "application/pdf",
                             "content-disposition": f'attachment; filename="{download.suggested_filename}"'},
                    content=content,
                    request=httpx.Request("GET", start_url),
                )
            except Exception as exc:
                raise SourceUnavailable(
                    f"{source} browser step '{stage}' failed: {_safe_error(exc)}"
                ) from exc
            finally:
                await browser.close()

class EgrulParser(RegistryParser):
    source = "egrul"

    async def fetch(self, client: httpx.AsyncClient, inn: str, ogrnip: str | None, fio: str) -> httpx.Response:
        """Скачивает официальную PDF-выписку через форму ФНС, как это делает сайт."""
        return await self._download_fns_pdf(inn, "egrul")


class PbParser(RegistryParser):
    source = "pb"

    async def fetch(self, client: httpx.AsyncClient, inn: str, ogrnip: str | None, fio: str) -> httpx.Response:
        """Скачивает выписку ЕГРИП из карточки ИП в сервисе ФНС."""
        return await self._download_fns_pdf(inn, "pb")


class FedresursParser(RegistryParser):
    source, url = "fedresurs", settings.fedresurs_url

    async def fetch(self, client: httpx.AsyncClient, inn: str, ogrnip: str | None, fio: str) -> httpx.Response:
        """Открывает публичный поиск по организациям и ИП на Федресурсе."""
        entities_url = urljoin(self.url.rstrip("/") + "/", "entities")
        return await client.get(entities_url, params={"searchString": inn})


class KadParser(RegistryParser):
    source, url = "kad", settings.kad_url

    async def fetch(self, client: httpx.AsyncClient, inn: str, ogrnip: str | None, fio: str) -> httpx.Response:
        """Ищет арбитражные дела через официальный endpoint поисковой формы КАД."""
        base_url = self.url.rstrip("/") + "/"
        search_url = urljoin(base_url, "Kad/SearchInstances")
        headers = {
            "Origin": self.url.rstrip("/"),
            "Referer": self.url,
            "x-date-format": "iso",
            "Content-Type": "application/json",
        }
        # Сначала получаем обычную cookie-сессию сайта, как это делает браузерная форма.
        await client.get(self.url)
        payload = {
            "Page": 1,
            "Count": 25,
            "Courts": [],
            "DateFrom": None,
            "DateTo": None,
            "Sides": [{"Name": inn, "Type": -1}],
            "Judges": [],
            "CaseNumbers": [],
            "WithVKSInstances": False,
        }
        return await client.post(search_url, json=payload, headers=headers)


def _safe_error(error: Exception | None) -> str:
    """Возвращает короткую ошибку без ИНН, ФИО и query-параметров URL."""
    if error is None:
        return "unknown error"
    message = str(error).splitlines()[0][:300]
    message = re.sub(r"(?i)(inn|ogrnip|fio|query|token)=([^&\s,;]+)", r"\1=[redacted]", message)
    message = re.sub(r"https?://[^\s'\"]+", "[URL hidden]", message)
    return message
