"""Сохраняет старую Listing-схему и подготавливает базу к миграциям новой формы."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def adopt_existing_schema() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.begin() as connection:
            old_table_exists = await connection.scalar(text("SELECT to_regclass('public.listings') IS NOT NULL"))
            version_table_exists = await connection.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
            if old_table_exists and not version_table_exists:
                # Existing releases used create_all without Alembic. Treat their
                # property listings as revision 001; revision 002 renames them.
                await connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                await connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001_listings')"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(adopt_existing_schema())
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=Path(__file__).parent, check=True)
