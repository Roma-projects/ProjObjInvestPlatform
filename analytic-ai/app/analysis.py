"""Детерминированные red flags и безопасный резервный отчёт, если Qwen недоступен."""

from __future__ import annotations

from typing import Any


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def detect_red_flags(data: dict[str, Any], registry: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Проверяет объективные финансовые расхождения и доступность данных реестра."""
    flags: list[dict[str, str]] = []
    months = data.get("monthly_financials") or []
    for month in months:
        revenue = _num(month.get("revenue"))
        expenses = _num(month.get("total_expenses"))
        profit = _num(month.get("net_profit"))
        label = str(month.get("month", "unknown"))
        if profit > revenue:
            flags.append({"code": "FIN-001", "severity": "critical", "evidence": f"net_profit exceeds revenue in {label}"})
        if revenue and abs(revenue - expenses - profit) > revenue * 0.05:
            flags.append({"code": "FIN-002", "severity": "high", "evidence": f"financial equation differs by over 5% in {label}"})
        cost_items = sum(_num(month.get(field)) for field in (
            "rent_expenses", "payroll_expenses", "purchases_expenses", "utilities_expenses",
            "taxes_expenses", "marketing_expenses", "other_expenses"))
        if expenses and abs(cost_items - expenses) > expenses * 0.10:
            flags.append({"code": "FIN-003", "severity": "medium", "evidence": f"expense categories differ by over 10% in {label}"})
    revenues = [_num(item.get("revenue")) for item in months]
    if revenues and all(value % 10000 == 0 for value in revenues):
        flags.append({"code": "FIN-004", "severity": "medium", "evidence": "all monthly revenue values are multiples of 10000"})
    average_profit = sum(_num(item.get("net_profit")) for item in months) / len(months) if months else 0
    price = _num(data.get("sale_price"))
    assets = sum(_num(item.get("equipment_value")) for item in (data.get("equipment_list") or [])) + _num(data.get("stock_value"))
    payback = price / average_profit if average_profit > 0 else None
    if payback is not None and payback < 6:
        flags.append({"code": "FIN-005", "severity": "high", "evidence": "estimated payback is under six months"})
    if average_profit <= 0 and price > assets:
        flags.append({"code": "FIN-005", "severity": "high", "evidence": "business is unprofitable and price exceeds declared assets"})
    if data.get("registry_check") == "invalid_inn":
        flags.append({"code": "REG-007", "severity": "high", "evidence": "seller INN failed format or checksum validation"})
    if registry and registry.get("status") not in (None, "действующая", "active"):
        flags.append({"code": "REG-001", "severity": "critical", "evidence": "registry record is not active"})
    if registry and registry.get("ogrnip") and data.get("seller_ogrnip") and registry["ogrnip"] != data["seller_ogrnip"]:
        flags.append({"code": "REG-003", "severity": "high", "evidence": "registry OGRNIP differs from seller declaration"})
    return flags


def fallback_report(data: dict[str, Any], registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Returns a conservative report; missing a configured LLM never auto-approves a listing."""
    flags = detect_red_flags(data, registry)
    months = data.get("monthly_financials") or []
    revenues = [_num(item.get("revenue")) for item in months]
    profits = [_num(item.get("net_profit")) for item in months]
    avg_revenue = sum(revenues) / len(revenues) if revenues else 0
    avg_profit = sum(profits) / len(profits) if profits else 0
    price = _num(data.get("sale_price"))
    payback = round(price / avg_profit, 2) if avg_profit > 0 else None
    severity_score = sum({"critical": 40, "high": 20, "medium": 10}.get(item["severity"], 0) for item in flags)
    moderation = "requires_moderation" if flags or not months else "requires_moderation"
    return {
        "red_flags": flags, "red_flag_score": min(100, severity_score),
        "moderation_status": moderation,
        "moderation_reasons": [item["code"] for item in flags] or ["AI endpoint is not configured; human review required"],
        "metrics_summary": {"average_monthly_revenue": round(avg_revenue, 2),
                            "average_monthly_net_profit": round(avg_profit, 2), "payback_months": payback},
        "content_moderation": [],
        "registry_match_report": {"status": data.get("registry_check", "skipped"), "extract": registry or {}},
        "price_assessment": {"fair_range_min": round(avg_profit * 24, 2) if avg_profit > 0 else None,
                             "fair_range_max": round(avg_profit * 48, 2) if avg_profit > 0 else None,
                             "verdict": "needs_human_review"},
        "forecast": {"horizon_months": 12, "direction": "unknown", "confidence": 0.0},
        "moderator_report": {"red_flags": flags, "review_required": True},
        "user_analytics": {"average_monthly_revenue": round(avg_revenue, 2),
                           "average_monthly_net_profit": round(avg_profit, 2),
                           "payback_months": payback},
    }
