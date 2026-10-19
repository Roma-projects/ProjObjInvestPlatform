"""Ручной direct_mode запуск Parsers без RabbitMQ.

Порядок источников параметров: CLI, переданный JSON, затем TEST_DATA.
Запускайте из каталога parsers командой `python -m tests.test_run`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys
import uuid
from typing import Any

# Позволяет запускать файл из корня проекта: app/ находится внутри parsers/.
PARSERS_DIR = Path(__file__).resolve().parents[1]
if str(PARSERS_DIR) not in sys.path:
    sys.path.insert(0, str(PARSERS_DIR))

from app.models import ParserRequest
from app.storage import MongoStorage
from app.worker import ParserWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# HTTPX включает query-параметры в URL логов; там могут быть персональные данные.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("parsers.test_run")

# Тестовый синтетический ИНН; подмените на тестовый ИНН, разрешённый для вашего прогона.
TEST_DATA = """
{
  "inn": "780415587178",
  "fio": "Шальнов Александр Витальевич",
  "status": "ip",
  "ogrnip": "304780408600170",
  "sources": ["egrul", "pb", "fedresurs", "kad"],
  "ttl_seconds": 120
}
"""


async def test(inn: str | None = None, fio: str | None = None, status: str | None = None,
              test_data_json: str | None = None, direct_mode: bool = True,
              sources: list[str] | None = None) -> dict[str, Any]:
    """Обрабатывает один запрос синхронно и сохраняет его в parsers_db_test."""
    if not direct_mode:
        raise ValueError("Only direct_mode is supported by this local runner")
    data = json.loads(test_data_json) if test_data_json else json.loads(TEST_DATA)
    if inn is not None:
        data["inn"] = inn
    if fio is not None:
        data["fio"] = fio
    if status is not None:
        data["status"] = status
    if sources:
        data["sources"] = sources
    request = ParserRequest(
        correlation_id=str(uuid.uuid4()), reply_to="test.local.reply",
        listing_id=str(uuid.uuid4()), **data,
    )
    logger.info("Парсеры: источники=%s; личные значения в лог не выводятся", request.sources)
    database_url = "mongodb://localhost:27017/parsers_db_test"
    storage = MongoStorage(database_url)
    await storage.connect()
    try:
        result = await ParserWorker(storage).process(request)
        output = result.model_dump(mode="json")
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return output
    finally:
        await storage.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ручной запуск Parsers без RabbitMQ")
    parser.add_argument("--inn")
    parser.add_argument("--fio")
    parser.add_argument("--status", choices=["ip", "self_employed"])
    parser.add_argument("--sources", nargs="+", choices=["egrul", "pb", "fedresurs", "kad"],
                        help="Запустить только указанные источники")
    parser.add_argument("--test-data", help="JSON-строка; CLI-поля имеют приоритет над ней")
    args = parser.parse_args()
    asyncio.run(test(args.inn, args.fio, args.status, args.test_data, sources=args.sources))


if __name__ == "__main__":
    main()
