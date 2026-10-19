"""Сохраняет скачанные документы на диск и технические записи в MongoDB."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings

settings = get_settings()


class LocalStorage:
    """Ограничивает все файлы каталогом одного объявления внутри parsers_storage."""

    def __init__(self, listing_id: str) -> None:
        """Создаёт отдельную папку для файлов одного объявления."""
        self.directory = (Path(settings.parsers_storage_dir) / listing_id).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, file_name: str, content: bytes) -> Path:
        """Сохраняет скачанный документ под безопасным именем внутри папки объявления."""
        safe_name = PurePosixPath(file_name).name
        path = (self.directory / safe_name).resolve()
        if self.directory not in path.parents:
            raise ValueError("Invalid parser file path")
        path.write_bytes(content)
        return path


class MongoStorage:
    """Хранит задания, извлечённые сведения и аудит файлов отдельно от других сервисов."""

    def __init__(self, uri: str | None = None) -> None:
        """Подключается к MongoDB и выбирает коллекции Parsers."""
        self.client = AsyncIOMotorClient(uri or settings.mongodb_url)
        database = self.client.get_default_database()
        self.tasks = database["parser_tasks"]
        self.extracted = database["extracted_data"]
        self.files = database["downloaded_files"]

    async def connect(self) -> None:
        """Создаёт индексы, нужные для быстрых и повторяемых записей."""
        await self.tasks.create_index("correlation_id", unique=True)
        await self.extracted.create_index("listing_id", unique=True)
        await self.files.create_index([("listing_id", 1), ("source", 1)])

    async def close(self) -> None:
        """Закрывает соединение с MongoDB при остановке сервиса."""
        self.client.close()

    async def record_file(self, listing_id: str, source: str, path: Path, url: str, mime: str) -> None:
        """Записывает путь, тип, размер и контрольную сумму скачанного файла."""
        content = path.read_bytes()
        item = {
            "listing_id": listing_id, "source": source, "file_path": str(path),
            "original_url": url, "file_size_bytes": len(content), "mime_type": mime,
            "sha256": hashlib.sha256(content).hexdigest(), "downloaded_at": datetime.now(timezone.utc),
        }
        await self.files.insert_one(item)
