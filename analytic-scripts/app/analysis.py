"""Формулы финансового отчёта: здесь нет случайности и обращений к внешним API."""

from __future__ import annotations

from typing import Any


def _number(value: Any) -> float:
    """Превращает пустые поля формы в ноль, чтобы расчёты не падали."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _ratio(value: float, base: float) -> float | None:
    return round(value / base, 4) if base else None


def _consistency(name: str, left: float, right: float, tolerance: float) -> dict[str, Any]:
    difference = abs(left - right)
    allowed = abs(right) * tolerance
    return {"check": name, "status": "ok" if difference <= allowed else "warning",
            "difference": round(difference, 2), "allowed_difference": round(allowed, 2)}


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    """Вычисляет доходность, окупаемость, сезонность и сверки для Listing."""
    months = sorted(data.get("monthly_financials") or [], key=lambda row: str(row.get("month", "")))
    revenues = [_number(row.get("revenue")) for row in months]
    profits = [_number(row.get("net_profit")) for row in months]
    expenses = [_number(row.get("total_expenses")) for row in months]
    avg_revenue = sum(revenues) / len(revenues) if revenues else 0.0
    avg_profit = sum(profits) / len(profits) if profits else 0.0
    sale_price = _number(data.get("sale_price"))
    cost_keys = ("rent_expenses", "payroll_expenses", "purchases_expenses", "utilities_expenses",
                 "taxes_expenses", "marketing_expenses", "other_expenses")
    cost_totals = {key: sum(_number(month.get(key)) for month in months) for key in cost_keys}
    total_expenses = sum(expenses)
    expense_percentages = {key.removesuffix("_expenses"): round(value / total_expenses * 100, 2)
                           if total_expenses else None for key, value in cost_totals.items()}
    declared_costs = [sum(_number(month.get(key)) for key in cost_keys) for month in months]
    consistency = []
    for index, month in enumerate(months):
        revenue = revenues[index]
        consistency.append(_consistency(f"net_profit:{month.get('month')}",
                                        revenue - expenses[index], profits[index], 0.05))
        consistency.append(_consistency(f"expense_items:{month.get('month')}",
                                        declared_costs[index], expenses[index], 0.10))
        staff_total = sum(_number(person.get("salary")) * _number(person.get("count"))
                          for person in (data.get("staff_details") or []))
        consistency.append(_consistency(f"payroll:{month.get('month')}",
                                        _number(month.get("payroll_expenses")), staff_total, 0.05))
        expected_revenue = _number(data.get("average_check")) * _number(data.get("monthly_orders"))
        if expected_revenue:
            consistency.append(_consistency(f"orders_revenue:{month.get('month')}", revenue, expected_revenue, 0.15))
    trend = "stable"
    if len(revenues) >= 2:
        if all(a < b for a, b in zip(revenues, revenues[1:])):
            trend = "growth"
        elif all(a > b for a, b in zip(revenues, revenues[1:])):
            trend = "decline"
        else:
            seasonal_months = set(data.get("seasonality_months") or [])
            if seasonal_months and any(_number(str(month.get("month", "-1"))[-2:]) in seasonal_months and revenue > avg_revenue
                                       for month, revenue in zip(months, revenues)):
                trend = "seasonal"
    average_staff = _number(data.get("staff_count"))
    rent = cost_totals["rent_expenses"] / len(months) if months else 0
    seasonality = [{"month": row.get("month"), "index": _ratio(revenues[i], avg_revenue)}
                   for i, row in enumerate(months)]
    return {
        "financial_metrics": {
            "average_monthly_revenue": round(avg_revenue, 2),
            "average_monthly_net_profit": round(avg_profit, 2),
            "payback_months": round(sale_price / avg_profit, 2) if avg_profit > 0 else None,
            "profitability_percent_by_month": [round(_ratio(profits[i], revenues[i]) * 100, 2)
                                                 if revenues[i] else None for i in range(len(months))],
            "average_profitability_percent": round(avg_profit / avg_revenue * 100, 2) if avg_revenue else None,
            "expense_structure_percent": expense_percentages,
            "debt_load_months": round(_number(data.get("monthly_loan_payments")) / avg_profit, 2)
            if avg_profit > 0 else None,
            "rent_per_sqm": round(rent / _number(data.get("area_sqm")), 2) if data.get("area_sqm") else None,
            "revenue_per_employee": round(avg_revenue / average_staff, 2) if average_staff else None,
            "assets_value": round(sum(_number(item.get("equipment_value")) for item in (data.get("equipment_list") or []))
                                  + _number(data.get("stock_value")), 2),
        },
        "revenue_trend": trend,
        "charts": {
            "revenue_line": [{"month": row.get("month"), "value": revenues[i]} for i, row in enumerate(months)],
            "profit_line": [{"month": row.get("month"), "value": profits[i]} for i, row in enumerate(months)],
            "expenses_pie": [{"name": key.removesuffix("_expenses"), "value": round(value, 2)}
                             for key, value in cost_totals.items()],
            "seasonality_bar": seasonality,
            "payback_gauge": {"sale_price": sale_price, "average_net_profit": round(avg_profit, 2),
                              "months": round(sale_price / avg_profit, 2) if avg_profit > 0 else None},
        },
        "consistency_report": consistency,
    }
