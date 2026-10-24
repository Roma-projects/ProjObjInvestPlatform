# Отчёт Analytic Scripts

**Тренд выручки:** growth

[Открыть интерактивный HTML-отчёт](./analytic_report.html)

## Финансовые метрики

| Метрика | Значение |
|---|---:|
| average_monthly_revenue | 1933333.33 |
| average_monthly_net_profit | 353333.33 |
| payback_months | 33.96 |
| profitability_percent_by_month | [17.78, 18.42, 18.57] |
| average_profitability_percent | 18.28 |
| expense_structure_percent / rent | 14.77 |
| expense_structure_percent / payroll | 14.77 |
| expense_structure_percent / purchases | 48.52 |
| expense_structure_percent / utilities | 1.69 |
| expense_structure_percent / taxes | 4.64 |
| expense_structure_percent / marketing | 1.27 |
| expense_structure_percent / other | 2.95 |
| debt_load_months | 0.14 |
| rent_per_sqm | 2745.1 |
| revenue_per_employee | 386666.67 |
| assets_value | 1118000.0 |

Графики и таблица проверок находятся в HTML-отчёте.

## Проверка согласованности

| Проверка | Статус | Разница | Допуск |
|---|---|---:|---:|
| net_profit:2026-01 | ok | 0.0 | 16000.0 |
| expense_items:2026-01 | ok | 110000.0 | 148000.0 |
| payroll:2026-01 | warning | 40000.0 | 15500.0 |
| orders_revenue:2026-01 | ok | 180000.0 | 297000.0 |
| net_profit:2026-02 | ok | 0.0 | 17500.0 |
| expense_items:2026-02 | warning | 470000.0 | 155000.0 |
| payroll:2026-02 | warning | 310000.0 | 15500.0 |
| orders_revenue:2026-02 | ok | 80000.0 | 297000.0 |
| net_profit:2026-03 | ok | 0.0 | 19500.0 |
| expense_items:2026-03 | ok | 40000.0 | 171000.0 |
| payroll:2026-03 | warning | 40000.0 | 15500.0 |
| orders_revenue:2026-03 | ok | 120000.0 | 297000.0 |
