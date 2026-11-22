import asyncio
import re
from urllib.parse import unquote, urlsplit

import asyncpg

from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    parsed = urlsplit(settings.database_url.replace("+asyncpg", ""))
    database_name = unquote(parsed.path.lstrip("/"))
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        raise ValueError("DATABASE_URL must use a simple PostgreSQL database name")
    connection = await asyncpg.connect(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        user=unquote(parsed.username or "postgres"),
        password=unquote(parsed.password or ""),
        database="postgres",
    )
    try:
        exists = await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", database_name)
        if not exists:
            await connection.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())

