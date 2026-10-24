"""Строит интерактивный Plotly HTML-отчёт и краткую Markdown-сводку."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR.parent))
from app.analysis import analyze, validate_input  # noqa: E402


def render_html(report: dict[str, Any], output: Path) -> None:
    """Создаёт автономную HTML-страницу с интерактивными Plotly-графиками."""
    metrics = report.get("financial_metrics") or {}
    charts = report.get("charts") or {}
    revenue, profit = charts.get("revenue_line") or [], charts.get("profit_line") or []
    expenses = charts.get("expenses_pie") or []
    seasonality = charts.get("seasonality_bar") or []
    gauge = charts.get("payback_gauge") or {}
    figure = make_subplots(
        rows=3, cols=2,
        specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "domain"}, {"type": "xy"}], [{"type": "indicator", "colspan": 2}, None]],
        subplot_titles=("Выручка и чистая прибыль", "Рентабельность по месяцам", "Структура расходов", "Индекс сезонности", "Окупаемость"),
        vertical_spacing=0.13,
    )
    figure.add_trace(go.Scatter(x=[x.get("month") for x in revenue], y=[x.get("value") for x in revenue], name="Выручка", mode="lines+markers", line={"color": "#635bff", "width": 3}, fill="tozeroy", fillcolor="rgba(99,91,255,.10)"), row=1, col=1)
    figure.add_trace(go.Scatter(x=[x.get("month") for x in profit], y=[x.get("value") for x in profit], name="Прибыль", mode="lines+markers", line={"color": "#16a085", "width": 3}), row=1, col=1)
    margins = metrics.get("profitability_percent_by_month") or []
    figure.add_trace(go.Bar(x=[x.get("month") for x in revenue[:len(margins)]], y=margins, name="Рентабельность, %", marker_color="#16a085"), row=1, col=2)
    figure.add_trace(go.Pie(labels=[x.get("name") for x in expenses], values=[x.get("value") for x in expenses], hole=.58, textinfo="label+percent", marker={"colors": ["#635bff", "#16a085", "#f5a623", "#e76f51", "#4f86c6", "#ae78d5", "#7b8794"]}), row=2, col=1)
    figure.add_trace(go.Bar(x=[x.get("month") for x in seasonality], y=[x.get("index") for x in seasonality], name="Индекс сезонности", marker_color="#f5a623"), row=2, col=2)
    payback = gauge.get("months")
    figure.add_trace(go.Indicator(mode="number+gauge", value=payback or 0, number={"suffix": " мес.", "valueformat": ".1f"}, gauge={"axis": {"range": [0, max(60, (payback or 0) * 1.2)]}, "bar": {"color": "#635bff"}, "steps": [{"range": [0, 24], "color": "#d8f3e8"}, {"range": [24, 48], "color": "#fff1d6"}, {"range": [48, 60], "color": "#fde2e2"}]}, title={"text": "Срок возврата цены продажи при средней чистой прибыли"}), row=3, col=1)
    figure.update_layout(template="plotly_white", height=1050, title={"text": "Финансовый обзор бизнеса", "x": .04, "font": {"size": 27}}, font={"family": "Inter, Arial", "color": "#263247"}, paper_bgcolor="#f5f7fb", plot_bgcolor="white", margin={"t": 100, "b": 45, "l": 55, "r": 40}, legend={"orientation": "h", "y": 1.08}, hovermode="x unified")
    consistency = report.get("consistency_report") or []
    table = go.Figure(data=[go.Table(header={"values": ["Проверка", "Статус", "Отклонение", "Допуск"], "fill_color": "#635bff", "font": {"color": "white", "size": 13}, "align": "left"}, cells={"values": [[x.get("check") for x in consistency], [x.get("status") for x in consistency], [x.get("difference") for x in consistency], [x.get("allowed_difference") for x in consistency]], "fill_color": [["#ffffff", "#f2f4fa"] * (len(consistency) // 2 + 1)], "align": "left", "height": 30})])
    trend = report.get("revenue_trend", "—")
    kpis = [
        ("Средняя выручка / месяц", metrics.get("average_monthly_revenue")),
        ("Средняя чистая прибыль", metrics.get("average_monthly_net_profit")),
        ("Средняя рентабельность", metrics.get("average_profitability_percent"), "%"),
        ("Окупаемость", payback, " мес."),
        ("Активы и товарный запас", metrics.get("assets_value")),
    ]
    cards = "".join(f'<div class="card"><small>{label}</small><strong>{value if value is not None else "Нет данных"}{unit if value is not None else ""}</strong></div>' for label, value, *rest in kpis for unit in [rest[0] if rest else ""])
    html = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Финансовый обзор</title><style>body{{margin:0;background:#f5f7fb;color:#263247;font:15px Inter,Arial,sans-serif}}main{{max-width:1200px;margin:auto;padding:38px 24px}}h1{{font-size:30px;margin:0}}.sub{{color:#738096;margin:8px 0 24px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}}.card{{background:white;border-radius:16px;padding:20px;box-shadow:0 5px 20px #2632470d}}small{{display:block;color:#738096;margin-bottom:12px}}strong{{font-size:22px}}section{{background:white;border-radius:16px;padding:10px;margin-top:18px;box-shadow:0 5px 20px #2632470d}}@media(max-width:600px){{main{{padding:20px 12px}}}}</style><main><h1>Финансовый обзор</h1><p class="sub">Тренд выручки: <b>{trend}</b> · суммы в исходной валюте объявления</p><div class="cards">{cards}</div><section>{figure.to_html(full_html=False, include_plotlyjs=True)}</section><h2>Проверка согласованности финансовых данных</h2><section>{table.to_html(full_html=False, include_plotlyjs=False)}</section></main></html>"""
    output.write_text(html, encoding="utf-8")


def render(report: dict[str, Any], output: Path) -> None:
    """Пишет краткую Markdown-сводку и рядом интерактивный HTML-отчёт."""
    metrics = report.get("financial_metrics") or {}
    html_path = output.with_suffix(".html")
    render_html(report, html_path)
    lines = ["# Отчёт Analytic Scripts", "", f"**Тренд выручки:** {report.get('revenue_trend', '—')}", "",
             f"[Открыть интерактивный HTML-отчёт](./{html_path.name})", "",
             "## Финансовые метрики", "", "| Метрика | Значение |", "|---|---:|"]
    for name, value in metrics.items():
        if isinstance(value, dict):
            for subname, subvalue in value.items():
                lines.append(f"| {name} / {subname} | {subvalue if subvalue is not None else 'нет данных'} |")
        else:
            lines.append(f"| {name} | {value if value is not None else 'нет данных'} |")
    lines.extend(["", "Графики и таблица проверок находятся в HTML-отчёте.", "", "## Проверка согласованности", "",
                  "| Проверка | Статус | Разница | Допуск |", "|---|---|---:|---:|"])
    for item in report.get("consistency_report") or []:
        lines.append(f"| {item.get('check')} | {item.get('status')} | {item.get('difference')} | {item.get('allowed_difference')} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Принимает JSON результата сервиса либо рассчитывает его из тестового события."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=TEST_DIR / "rabbit_listing_started.json")
    parser.add_argument("--result", type=Path, help="Файл JSON с ответом Analytic Scripts")
    parser.add_argument("--output", type=Path, default=TEST_DIR / "analytic_report.md")
    args = parser.parse_args()
    if args.result:
        report = json.loads(args.result.read_text(encoding="utf-8"))
    else:
        event = json.loads(args.input.read_text(encoding="utf-8"))
        report = analyze(validate_input(event.get("data_for_analytics")))
    render(report, args.output)
    print(f"Отчёты созданы: {args.output} и {args.output.with_suffix('.html')}")


if __name__ == "__main__":
    main()
