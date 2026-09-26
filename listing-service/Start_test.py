"""Для чего нужен этот файл:
Запускает микросервис listing-service отдельно через Uvicorn и выбирает папку приложения и порт.
"""

"""Listing Service — temporary local runner (Docker disabled)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    print("[listing-service] Starting on http://localhost:8002  docs: /docs")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8002",
            "--reload",
        ],
        cwd=str(ROOT),
        check=False,
    )


if __name__ == "__main__":
    main()
