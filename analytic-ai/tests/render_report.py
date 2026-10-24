"""Создаёт автономную HTML-панель с графиками и краткую Markdown-сводку."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder


def _money(value: Any) -> str:
    """Форматирует сумму в рублях, не добавляя отдельную библиотеку локалей."""
    try:
        return f"{float(value):,.0f} ₽".replace(",", " ")
    except (TypeError, ValueError):
        return "нет данных"


def _scenario_section(scenario: dict[str, Any], result: dict[str, Any], index: int) -> tuple[str, str, list[str]]:
    """Собирает карточку сценария с финансовыми графиками и данными модерации."""
    report = result.get("report", result)
    data = scenario.get("data_for_analytics", {})
    months = data.get("monthly_financials") or []
    labels = [str(item.get("month", "")) for item in months]
    revenues = [item.get("revenue") for item in months]
    profits = [item.get("net_profit") for item in months]
    expense_fields = ("rent_expenses", "payroll_expenses", "purchases_expenses", "utilities_expenses",
                      "taxes_expenses", "marketing_expenses", "other_expenses")
    latest = months[-1] if months else {}
    expense_values = [latest.get(key, 0) or 0 for key in expense_fields]
    expense_labels = ["Аренда", "Зарплата", "Закупки", "Коммунальные", "Налоги", "Маркетинг", "Прочее"]
    metrics = report.get("metrics_summary") or report.get("user_analytics") or {}
    price_assessment = report.get("price_assessment") or {}
    forecast = report.get("forecast") or {}
    price_min = price_assessment.get("fair_range_min", price_assessment.get("estimated_fair_price_min"))
    price_max = price_assessment.get("fair_range_max", price_assessment.get("estimated_fair_price_max"))
    average_profit = metrics.get("average_monthly_net_profit")
    if isinstance(average_profit, (int, float)) and average_profit > 0:
        # The conservative fallback range already used by Analytic AI is 24–48 monthly profits.
        price_min = price_min if price_min is not None else average_profit * 24
        price_max = price_max if price_max is not None else average_profit * 48
    forecast_direction = forecast.get("direction") or forecast.get("growth_trend") or "нет данных"
    forecast_direction = {"positive": "рост", "negative": "снижение", "stable": "стабильно"}.get(
        str(forecast_direction).lower(), forecast_direction)
    forecast_horizon = forecast.get("horizon_months") or 12
    confidence = forecast.get("confidence")
    confidence_label = f"{float(confidence) * 100:.0f}%" if isinstance(confidence, (int, float)) else "не указана моделью"
    forecast_details = []
    if forecast.get("projected_annual_revenue") is not None:
        forecast_details.append(f"выручка {_money(forecast['projected_annual_revenue'])} / год")
    if forecast.get("projected_annual_profit") is not None:
        forecast_details.append(f"прибыль {_money(forecast['projected_annual_profit'])} / год")
    forecast_detail_html = (f"<small>{html.escape('; '.join(forecast_details))}</small>"
                            if forecast_details else "<small>годовые значения не рассчитаны</small>")

    finance = go.Figure()
    finance.add_trace(go.Bar(name="Выручка", x=labels, y=revenues, marker_color="#4f46e5"))
    finance.add_trace(go.Scatter(name="Чистая прибыль", x=labels, y=profits, mode="lines+markers",
                                 line={"color": "#10b981", "width": 3}, yaxis="y2"))
    finance.update_layout(title="Выручка и чистая прибыль по месяцам", height=370, margin={"l": 55, "r": 55, "t": 65, "b": 50},
                          paper_bgcolor="white", plot_bgcolor="#f8fafc", legend={"orientation": "h", "y": 1.12},
                          xaxis={"title": "Месяц", "gridcolor": "#e2e8f0"},
                          yaxis={"title": "Выручка, ₽", "gridcolor": "#e2e8f0"},
                          yaxis2={"title": "Прибыль, ₽", "overlaying": "y", "side": "right"})
    pie = go.Figure(go.Pie(labels=expense_labels, values=expense_values, hole=0.58,
                           marker={"colors": ["#4f46e5", "#06b6d4", "#f59e0b", "#10b981", "#f43f5e", "#8b5cf6", "#94a3b8"]},
                           textinfo="label+percent"))
    pie.update_layout(title="Структура расходов за последний месяц", height=370, margin={"l": 15, "r": 15, "t": 65, "b": 20},
                      paper_bgcolor="white", showlegend=False)
    chart_ids = f"finance-{index}", f"expenses-{index}"
    # Use JSON encoding for chart payloads so embedded HTML remains valid JavaScript.
    charts = [
        f"Plotly.newPlot('{chart_ids[0]}',{json.dumps(finance.to_plotly_json()['data'], ensure_ascii=False, cls=PlotlyJSONEncoder)},{json.dumps(finance.to_plotly_json()['layout'], ensure_ascii=False, cls=PlotlyJSONEncoder)},{{responsive:true,displayModeBar:false}});",
        f"Plotly.newPlot('{chart_ids[1]}',{json.dumps(pie.to_plotly_json()['data'], ensure_ascii=False, cls=PlotlyJSONEncoder)},{json.dumps(pie.to_plotly_json()['layout'], ensure_ascii=False, cls=PlotlyJSONEncoder)},{{responsive:true,displayModeBar:false}});",
    ]

    status = report.get("moderation_status", "unknown")
    badge_class = "safe" if status == "auto_ok" else "review"
    photo_rows = []
    moderation = report.get("content_moderation") or []
    for item in moderation:
        if not isinstance(item, dict):
            continue
        photo_rows.append(
            "<tr><td><code>{}</code></td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(str(item.get("image_path", "—"))), html.escape(str(item.get("status", "—"))),
                html.escape(str(item.get("category", "—"))), html.escape(str(item.get("reason", "—"))))
        )
    photo_table = ("<table><thead><tr><th>Фото</th><th>Статус</th><th>Категория</th><th>Пояснение</th></tr></thead><tbody>"
                   + "".join(photo_rows) + "</tbody></table>" if photo_rows else "<p class='muted'>Нет подробных результатов по фото.</p>")
    title = html.escape(str(scenario.get("name", f"Сценарий {index}")))
    metric_cards = "".join([
        f"<div class='metric'><span>Средняя выручка</span><strong>{_money(metrics.get('average_monthly_revenue'))}</strong></div>",
        f"<div class='metric'><span>Средняя чистая прибыль</span><strong>{_money(metrics.get('average_monthly_net_profit'))}</strong></div>",
        f"<div class='metric'><span>Окупаемость</span><strong>{metrics.get('payback_months', 'нет данных')} мес.</strong></div>",
        f"<div class='metric'><span>Цена продажи</span><strong>{_money(data.get('sale_price'))}</strong></div>",
        f"<div class='metric'><span>Расчётный диапазон (24–48 мес. прибыли)</span><strong>{_money(price_min)} – {_money(price_max)}</strong></div>",
        f"<div class='metric'><span>Прогноз на {forecast_horizon} мес.</span><strong>{html.escape(str(forecast_direction))}</strong>{forecast_detail_html}</div>",
        f"<div class='metric'><span>Уверенность прогноза</span><strong>{confidence_label}</strong></div>",
        f"<div class='metric'><span>Баллы риска (порог 5)</span><strong>{report.get('red_flag_score', 'нет данных')} · {html.escape(str(report.get('red_flag_rating', '—')))}</strong></div>",
    ])
    flags = report.get("red_flags") or []
    flag_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(str(item.get("code", "—"))), html.escape(str(item.get("severity", "—"))),
            html.escape(str(item.get("evidence", "—"))))
        for item in flags if isinstance(item, dict)
    )
    flags_table = ("<table><thead><tr><th>Код</th><th>Важность</th><th>Основание</th></tr></thead><tbody>"
                   + flag_rows + "</tbody></table>" if flag_rows else "<p class='muted'>Явных red flags не обнаружено.</p>")
    listing_policy = scenario.get("expected_listing_policy")
    listing_policy_html = ""
    if isinstance(listing_policy, dict):
        listing_policy_html = (
            "<h3>Отдельное решение Listing</h3><p>" +
            html.escape(str(listing_policy.get("status", "—"))) + " / " +
            html.escape(str(listing_policy.get("verification_status", "—"))) + ". " +
            html.escape(str(listing_policy.get("reason", ""))) + "</p>"
        )
    expected_flags = scenario.get("expected_red_flags") or []
    expected_score = scenario.get("expected_red_flag_score")
    expected_rating = scenario.get("expected_red_flag_rating")
    expected_risk_html = (
        f"<p class='muted'>Ожидалось по фикстуре: {html.escape(', '.join(expected_flags) or 'без red flags')}; "
        f"баллы {html.escape(str(expected_score)) if expected_score is not None else '—'} (порог 5); "
        f"уровень {html.escape(str(expected_rating or '—'))}.</p>"
    )
    section = f"""
    <section class="scenario">
      <div class="scenario-head"><div><p class="eyebrow">СЦЕНАРИЙ {index:02}</p><h2>{title}</h2></div>
        <span class="badge {badge_class}">{html.escape(status)}</span></div>
      <div class="metrics">{metric_cards}</div>
      <div class="charts"><div id="{chart_ids[0]}"></div><div id="{chart_ids[1]}"></div></div>
      <h3>Финансовые риски</h3>{expected_risk_html}{flags_table}
      <h3>Проверка фотографий</h3>{photo_table}
      {listing_policy_html}
      <p class="muted">Причины статуса AI: {html.escape(', '.join(map(str, report.get('moderation_reasons') or ['для текущего статуса не требуются'])))}</p>
    </section>"""
    md_lines = [f"## {title}", "", f"- Статус модерации: **{status}**",
                f"- Средняя месячная выручка: {_money(metrics.get('average_monthly_revenue'))}",
                f"- Средняя месячная чистая прибыль: {_money(metrics.get('average_monthly_net_profit'))}",
                f"- Окупаемость: {metrics.get('payback_months', 'нет данных')} мес.",
                f"- Расчётный диапазон (24–48 мес. прибыли): {_money(price_min)} – {_money(price_max)}",
                f"- Прогноз: {forecast_direction} на {forecast_horizon} мес.; уверенность {confidence_label}",
                f"- Баллы риска: {report.get('red_flag_score', 'нет данных')} / 5; уровень {report.get('red_flag_rating', '—')}", "", "Red flags:"]
    if isinstance(listing_policy, dict):
        md_lines.extend(["", f"- Отдельный статус Listing: **{listing_policy.get('status', '—')} / {listing_policy.get('verification_status', '—')}**",
                         f"- Основание Listing: {listing_policy.get('reason', '—')}"])
    md_lines.extend([f"- {item.get('code', '—')} ({item.get('severity', '—')}): {item.get('evidence', '—')}"
                     for item in flags if isinstance(item, dict)] or ["- Явных red flags не обнаружено."])
    md_lines.extend(["", f"- Ожидалось по фикстуре: {', '.join(expected_flags) or 'без red flags'}; "
                     f"баллы {expected_score if expected_score is not None else '—'} (порог 5), "
                     f"уровень {expected_rating or '—'}. "])
    if forecast_details:
        md_lines.append(f"- Значения прогноза: {'; '.join(forecast_details)}")
    md_lines.extend(["", "Фото:"])
    md_lines.extend([f"- `{item.get('image_path', '—')}` — {item.get('status', '—')}: {item.get('reason', '—')}"
                     for item in moderation if isinstance(item, dict)] or ["- Нет подробных результатов."])
    md_lines.append("")
    return section, "\n".join(md_lines), charts


def render(result_path: Path, scenarios_path: Path, html_path: Path, markdown_path: Path) -> None:
    """Соединяет входные сценарии с ответами AI и сохраняет HTML и Markdown."""
    results = json.loads(result_path.read_text(encoding="utf-8"))
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))["scenarios"]
    by_name = {str(item.get("scenario")): item for item in results.get("results", [])}
    sections: list[str] = []
    markdown: list[str] = ["# Отчёт Analytic AI", "", "Графики ниже встроены в отдельный файл `report.html`.", ""]
    scripts: list[str] = []
    for index, scenario in enumerate(scenarios, 1):
        result = by_name.get(str(scenario.get("name")))
        if result is None:
            continue
        section, summary, chart_scripts = _scenario_section(scenario, result, index)
        sections.append(section)
        scripts.extend(chart_scripts)
        markdown.append(summary)
    html_path.write_text(f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Отчёт Analytic AI</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#f1f5f9;color:#172033;font:15px/1.55 Inter,'Segoe UI',Arial,sans-serif}}main{{max-width:1280px;margin:auto;padding:40px 24px}}header{{padding:32px;border-radius:24px;background:linear-gradient(125deg,#312e81,#4f46e5 60%,#06b6d4);color:white;box-shadow:0 16px 40px #312e8133}}h1{{font-size:clamp(28px,4vw,42px);margin:4px 0}}header p{{opacity:.9;margin:0}}.scenario{{margin:28px 0;padding:28px;background:white;border:1px solid #e2e8f0;border-radius:20px;box-shadow:0 8px 28px #0f172a0a}}.scenario-head{{display:flex;align-items:center;justify-content:space-between;gap:20px}}h2{{margin:0;font-size:25px}}h3{{margin:24px 0 10px}}.eyebrow{{margin:0;color:#64748b;font-size:12px;font-weight:700;letter-spacing:.1em}}.badge{{padding:7px 13px;border-radius:999px;font-weight:700;white-space:nowrap}}.safe{{color:#047857;background:#d1fae5}}.review{{color:#b45309;background:#fef3c7}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.metric{{padding:16px;border-radius:14px;background:#f8fafc;border:1px solid #e2e8f0}}.metric span{{display:block;color:#64748b;font-size:13px}}.metric strong{{display:block;margin-top:5px;font-size:20px}}.metric small{{display:block;margin-top:4px;color:#64748b;font-size:12px;line-height:1.4}}.charts{{display:grid;grid-template-columns:1.25fr 1fr;gap:18px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:11px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #e2e8f0}}th{{color:#475569;background:#f8fafc}}code{{overflow-wrap:anywhere;color:#4338ca}}.muted{{color:#64748b;font-size:13px}}footer{{padding:20px;color:#64748b;text-align:center}}@media(max-width:800px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.charts{{grid-template-columns:1fr}}main{{padding:18px 12px}}.scenario{{padding:18px}}}}@media(max-width:480px){{.metrics{{grid-template-columns:1fr}}table{{font-size:12px}}th,td{{padding:7px}}}}</style></head>
    <body><main><header><p>АНАЛИЗ ОБЪЯВЛЕНИЯ</p><h1>Отчёт Analytic AI</h1><p>Финансовые показатели и модерация фотографий по тестовым RabbitMQ-событиям</p></header>{''.join(sections)}<footer>Сгенерировано локально из тестовых JSON-данных.</footer></main><script>{get_plotlyjs()}</script><script>{' '.join(scripts)}</script></body></html>""", encoding="utf-8")
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")
    print(f"Созданы визуальный отчёт {html_path} и Markdown-сводка {markdown_path}")


def main() -> None:
    """Принимает пути к файлам, чтобы пересобирать отчёт без повторного запроса к AI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=Path(__file__).with_name("results.json"))
    parser.add_argument("--scenarios", type=Path, default=Path(__file__).with_name("rabbit_scenarios.json"))
    parser.add_argument("--html", type=Path, default=Path(__file__).with_name("report.html"))
    parser.add_argument("--markdown", type=Path, default=Path(__file__).with_name("report.md"))
    args = parser.parse_args()
    render(args.result, args.scenarios, args.html, args.markdown)


if __name__ == "__main__":
    main()
