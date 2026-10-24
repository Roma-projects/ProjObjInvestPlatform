"""Локально проигрывает тестовые RabbitMQ-события через Analytic AI и Polza vision API."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any
from dotenv import load_dotenv

from render_report import render

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parents[1]


async def run(scenarios_path: Path, result_path: Path, public_upload_dir: Path) -> None:
    """Читает секреты из локальных env-файлов, выполняет сценарии и пишет JSON-ответы."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    load_dotenv(PROJECT_ROOT / "analytic-ai" / ".env", override=False)
    if not os.getenv("POLZA_API_KEY") and not os.getenv("QWEN_API_KEY"):
        raise SystemExit("AI ключ не задан в analytic-ai/.env или переменных окружения.")
    os.environ.setdefault("POLZA_BASE_URL", "https://polza.ai/api/v1")
    # Тест всегда отправляет сценарии проверенной модели, даже если в shell/.env задана другая.
    os.environ["POLZA_MODEL"] = "google/gemini-3.8-flash"
    os.environ["PUBLIC_UPLOAD_DIR"] = str(public_upload_dir.resolve())
    service_dir = Path(os.environ.get("ANALYTIC_AI_DIR", PROJECT_ROOT / "analytic-ai"))
    sys.path.insert(0, str(service_dir))
    from app.model_client import VisionAnalyzer  # noqa: PLC0415

    print("Модель для тестового запуска: google/gemini-3.8-flash")
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))["scenarios"]
    analyzer = VisionAnalyzer()
    results: list[dict[str, Any]] = []
    try:
        for scenario in scenarios:
            payload = scenario["data_for_analytics"]
            report = await analyzer.analyze(payload, registry=scenario.get("registry_extract"))
            results.append({
                "event": "listing.ai.analysis.completed",
                "event_id": f"{scenario['correlation_id']}:ai",
                "correlation_id": scenario["correlation_id"],
                "listing_id": scenario["listing_id"],
                "user_id": scenario["user_id"],
                "scenario": scenario["name"],
                "test_expectations": {
                    "moderation_status": scenario["expected_status"],
                    "listing_policy": scenario.get("expected_listing_policy"),
                    "red_flags": scenario.get("expected_red_flags", []),
                    "red_flag_score": scenario.get("expected_red_flag_score"),
                    "red_flag_rating": scenario.get("expected_red_flag_rating"),
                },
                **report,
            })
    finally:
        await analyzer.close()
    result_path.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Создан JSON с результатами {len(results)} сценариев: {result_path}")
    render(result_path, scenarios_path, result_path.with_name("report.html"), result_path.with_name("report.md"))
    for item in results:
        expectations = item["test_expectations"]
        print(f"{item['scenario']}: AI={item['moderation_status']}; "
              f"risk={item.get('red_flag_score', 0)} ({item.get('red_flag_rating', '—')}); "
              f"red_flags={','.join(flag.get('code', '—') for flag in item.get('red_flags', [])) or 'none'}; "
              f"ожидалось AI={expectations['moderation_status']}")
        listing_policy = expectations.get("listing_policy")
        if isinstance(listing_policy, dict):
            print(f"  Listing policy: {listing_policy.get('status')} / "
                  f"{listing_policy.get('verification_status')} — {listing_policy.get('reason')}")


def main() -> None:
    """Запускает два сценария из JSON; секрет задаётся отдельным key.txt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=TEST_DIR / "rabbit_scenarios.json")
    parser.add_argument("--result", type=Path, default=TEST_DIR / "results.json")
    parser.add_argument("--public-upload-dir", type=Path, default=PROJECT_ROOT / "public_photo")
    args = parser.parse_args()
    asyncio.run(run(args.scenarios, args.result, args.public_upload_dir))


if __name__ == "__main__":
    main()
