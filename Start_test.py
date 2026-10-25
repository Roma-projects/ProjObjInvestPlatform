"""Для чего нужен этот файл:
Запускает все микросервисы локально в отдельных процессах. Здесь заданы сервисы и порты; Ctrl+C останавливает запущенные процессы.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SERVICES = [
    ("api-gateway", 8000),
]


def main() -> None:
    processes: list[subprocess.Popen] = []

    print("=" * 60)
    print(" Real Estate Business Platform — локальный API Gateway")
    print(" Для полного стека используйте: docker compose up --build -d")
    print("=" * 60)

    for name, port in SERVICES:
        cwd = ROOT / name
        if not (cwd / "app" / "main.py").exists():
            print(f"[SKIP] {name}: app/main.py не найден")
            continue

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--reload",
        ]
        print(f"[START] {name} → http://localhost:{port}  (docs: /docs)")
        proc = subprocess.Popen(cmd, cwd=str(cwd))
        processes.append(proc)
        time.sleep(0.4)

    print("-" * 60)
    print("API docs:")
    for name, port in SERVICES:
        print(f"  {name:22s} http://localhost:{port}/docs")
    print("-" * 60)

    def _shutdown(*_args):
        print("\n[STOP] Останавливаем сервисы...")
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            dead = [p for p in processes if p.poll() is not None]
            if dead and len(dead) == len(processes):
                print("[WARN] Все процессы завершились")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()
