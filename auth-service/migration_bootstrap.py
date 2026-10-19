"""Подхватывает существующую Auth-схему до применения новых Alembic-миграций."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def adopt_existing_schema() -> None:
    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            users_exist = await connection.scalar(text("SELECT to_regclass('public.users') IS NOT NULL"))
            version_table_exists = await connection.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
            if users_exist and not version_table_exists:
                # The old app created tables directly; mark its schema as revision 001
                # so revision 002 can add fields without trying to recreate users.
                await connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
                await connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001_auth_users')"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(adopt_existing_schema())
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=Path(__file__).parent, check=True)
