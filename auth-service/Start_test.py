"""Для чего нужен этот файл:
Запускает микросервис auth-service отдельно через Uvicorn и выбирает папку приложения и порт.
"""

"""Auth Service — temporary local runner (Docker disabled)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    print("[auth-service] Starting on http://localhost:8001  docs: /docs")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8001",
            "--reload",
        ],
        cwd=str(ROOT),
        check=False,
    )


if __name__ == "__main__":
    main()
