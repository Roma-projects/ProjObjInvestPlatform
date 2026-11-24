const labels = {
  business_name: 'Название бизнеса', business_type: 'Сфера бизнеса', short_description: 'Краткое описание',
  full_description: 'Полное описание', sale_price: 'Цена продажи', stock_included: 'Товарный остаток включён',
  stock_value: 'Стоимость товарного остатка', property_type: 'Тип помещения', deal_composition: 'Состав сделки',
  transfer_method: 'Способ передачи', property_condition: 'Состояние помещения', area_sqm: 'Площадь, м²',
  equipment_list: 'Оборудование', staff_count: 'Количество сотрудников', staff_details: 'Состав команды',
  business_age_months: 'Возраст бизнеса, месяцев', has_licenses: 'Лицензии', has_contracts: 'Договоры', sale_reason: 'Причина продажи',
  has_documents: 'Наличие документов',
  monthly_financials: 'Финансовые данные по месяцам', average_check: 'Средний чек', monthly_orders: 'Заказов в месяц',
  monthly_clients_unique: 'Уникальных клиентов в месяц', repeat_customer_rate: 'Доля повторных клиентов',
  customer_base_size: 'Клиентская база', cost_structure: 'Структура расходов', seasonality_months: 'Сезонные месяцы',
  peak_hours: 'Часы пик', supplier_contracts: 'Договоры с поставщиками', supplier_details: 'Поставщики',
  debts_receivable: 'Дебиторская задолженность', debts_payable: 'Кредиторская задолженность', legal_claims: 'Судебные споры',
  legal_claims_details: 'Детали судебных споров', equipment_lease: 'Аренда оборудования', monthly_loan_payments: 'Платежи по кредитам',
  seller_name: 'Продавец', seller_status: 'Статус продавца', seller_inn: 'ИНН', seller_ogrnip: 'ОГРНИП',
  country: 'Страна', city: 'Город', street: 'Улица', registry_check: 'Статус проверки реестра', tax_system: 'Система налогообложения',
  financial_metrics: 'Финансовые показатели', revenue_trend: 'Динамика выручки', consistency_report: 'Сверки и проверки',
  red_flags: 'Риски и замечания', red_flag_score: 'Баллы риска', red_flag_rating: 'Уровень риска',
  moderation_status: 'Решение AI', moderation_reasons: 'Причины проверки', content_moderation: 'Проверка фотографий',
  registry_match_report: 'Проверка по реестру', price_assessment: 'Оценка цены', forecast: 'Прогноз бизнеса',
  moderator_report: 'Резюме для модератора', metrics_summary: 'Сводные показатели', user_analytics: 'Аналитические показатели',
  confidence: 'Уверенность', confidence_level: 'Уровень уверенности', assumptions: 'Допущения', valuation_method: 'Метод оценки',
  fair_range_min: 'Нижняя граница оценки', fair_range_max: 'Верхняя граница оценки',
  estimated_fair_value_min: 'Минимальная справедливая стоимость', estimated_fair_value_max: 'Максимальная справедливая стоимость',
  verdict: 'Заключение', direction: 'Направление', horizon_months: 'Горизонт прогноза, месяцев',
  projected_monthly_revenue_avg: 'Прогноз выручки в месяц', projected_monthly_net_profit_avg: 'Прогноз прибыли в месяц',
  annual_projected_profit: 'Прогноз прибыли за год', average_monthly_revenue: 'Средняя выручка в месяц',
  average_monthly_net_profit: 'Средняя чистая прибыль в месяц', payback_months: 'Окупаемость, месяцев',
  average_profitability_percent: 'Средняя рентабельность', expense_structure_percent: 'Структура расходов, %',
  debt_load_months: 'Кредитная нагрузка, месяцев', rent_per_sqm: 'Аренда за м²', revenue_per_employee: 'Выручка на сотрудника',
  assets_value: 'Стоимость активов', check: 'Проверка', status: 'Статус', difference: 'Расхождение',
  allowed_difference: 'Допустимое расхождение', image_path: 'Фотография', category: 'Категория', reason: 'Пояснение',
  severity: 'Важность', evidence: 'Основание', recommendation: 'Рекомендация', review_required: 'Нужна ручная проверка',
  risk_level: 'Уровень риска', images_passed: 'Фото без замечаний', images_failed: 'Фото с замечаниями',
  requires_manual_doc_request: 'Нужно запросить документы', payback_period_months: 'Окупаемость, месяцев',
};

const moneyFormat = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const labelFor = (key) => labels[key] || String(key).replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const moneyLike = /(price|revenue|profit|expense|value|salary|debt|assets|rent|check)/i;

function formatValue(key, value) {
  if (value === null || value === undefined || value === '') return 'Не указано';
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет';
  if (typeof value === 'number') {
    if (moneyLike.test(key)) return `${moneyFormat.format(value)} ₽`;
    if (/(percent|rate|confidence)$/i.test(key)) return `${(Math.abs(value) <= 1 && value !== 0 ? value * 100 : value).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`;
    return value.toLocaleString('ru-RU', { maximumFractionDigits: 2 });
  }
  if (typeof value === 'string') return value.replaceAll('_', ' ');
  return '';
}

function addData(grid, data, columns = 3) {
  let added = 0;
  Object.entries(data || {}).forEach(([key, value]) => {
    if (value === undefined) return;
    const card = document.createElement('article'); card.className = 'report-value';
    const label = document.createElement('span'); label.className = 'report-value__label'; label.textContent = labelFor(key);
    const content = document.createElement('div'); content.className = 'report-value__content';
    if (Array.isArray(value)) {
      if (!value.length) content.textContent = 'Нет данных';
      else {
        const list = document.createElement('ul'); list.className = 'report-value__list';
        value.forEach((entry) => {
          const row = document.createElement('li');
          row.textContent = entry && typeof entry === 'object'
            ? Object.entries(entry).map(([field, detail]) => `${labelFor(field)}: ${formatValue(field, detail)}`).join(' · ')
            : formatValue(key, entry);
          list.append(row);
        });
        content.append(list);
      }
    } else if (value && typeof value === 'object') {
      card.classList.add('report-value--nested');
      const nested = document.createElement('div'); nested.className = 'report-value__nested';
      addData(nested, value, 2); content.append(nested);
    } else content.textContent = formatValue(key, value);
    card.append(label, content); card.style.setProperty('--report-columns', String(columns)); grid.append(card); added += 1;
  });
  return added;
}

export function makeReportSection(title, data, className = '') {
  if (!data || typeof data !== 'object' || !Object.keys(data).length) return null;
  const section = document.createElement('section'); section.className = `analysis-block report-section ${className}`.trim();
  const heading = document.createElement('h2'); heading.className = 'section-title'; heading.textContent = title;
  const grid = document.createElement('div'); grid.className = 'report-grid';
  if (!addData(grid, data)) return null;
  section.append(heading, grid); return section;
}

export function makeRiskSparkline(score, rating) {
  const numericScore = Number(score);
  const normalized = Number.isFinite(numericScore) ? Math.max(0, Math.min(5, numericScore)) : 0;
  const wrapper = document.createElement('span'); wrapper.className = 'queue-risk-spark';
  wrapper.setAttribute('aria-hidden', 'true');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 72 26');
  const colorClass = `queue-risk-spark__bar--${rating || 'unknown'}`;
  for (let index = 0; index < 5; index += 1) {
    const bar = document.createElementNS(svg.namespaceURI, 'rect');
    bar.setAttribute('x', String(2 + index * 14)); bar.setAttribute('y', '5');
    bar.setAttribute('width', '10'); bar.setAttribute('height', '16'); bar.setAttribute('rx', '3');
    bar.setAttribute('class', `queue-risk-spark__bar ${index < normalized ? colorClass : ''}`.trim()); svg.append(bar);
  }
  wrapper.append(svg); return wrapper;
}

function addLineChart(grid, title, points, modifier = '') {
  const values = Array.isArray(points)
    ? points.map((point) => ({ label: point.month || point.label || '', value: Number(point.value ?? point.index) })).filter((point) => Number.isFinite(point.value))
    : [];
  if (values.length < 2) return false;
  const width = 720; const height = 210; const pad = { top: 22, right: 18, bottom: 38, left: 52 };
  const min = Math.min(0, ...values.map((point) => point.value)); const max = Math.max(1, ...values.map((point) => point.value));
  const plotW = width - pad.left - pad.right; const plotH = height - pad.top - pad.bottom; const span = max - min || 1;
  const coords = values.map((point, index) => ({ ...point, x: pad.left + index * plotW / (values.length - 1), y: pad.top + (max - point.value) * plotH / span }));
  const figure = document.createElement('figure'); figure.className = `moderation-chart ${modifier}`.trim();
  const caption = document.createElement('figcaption'); caption.textContent = title;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', `${title}: ${values.map((p) => `${p.label} ${p.value}`).join(', ')}`);
  [0, 0.5, 1].forEach((fraction) => {
    const y = pad.top + plotH * fraction; const line = document.createElementNS(svg.namespaceURI, 'line');
    line.setAttribute('x1', String(pad.left)); line.setAttribute('x2', String(width - pad.right)); line.setAttribute('y1', String(y));
    line.setAttribute('y2', String(y)); line.setAttribute('class', 'moderation-chart__grid'); svg.append(line);
  });
  const polyline = document.createElementNS(svg.namespaceURI, 'polyline');
  polyline.setAttribute('points', coords.map((p) => `${p.x},${p.y}`).join(' ')); polyline.setAttribute('class', 'moderation-chart__line'); svg.append(polyline);
  coords.forEach((point, index) => {
    const circle = document.createElementNS(svg.namespaceURI, 'circle'); circle.setAttribute('cx', String(point.x));
    circle.setAttribute('cy', String(point.y)); circle.setAttribute('r', '4'); circle.setAttribute('class', 'moderation-chart__point');
    const tip = document.createElementNS(svg.namespaceURI, 'title'); tip.textContent = `${point.label || `Точка ${index + 1}`}: ${point.value.toLocaleString('ru-RU')}`;
    circle.append(tip); svg.append(circle);
    if (index === 0 || index === coords.length - 1 || index === Math.floor(coords.length / 2)) {
      const label = document.createElementNS(svg.namespaceURI, 'text'); label.setAttribute('x', String(point.x));
      label.setAttribute('y', String(height - 10)); label.setAttribute('text-anchor', 'middle');
      label.setAttribute('class', 'moderation-chart__label'); label.textContent = point.label || String(index + 1); svg.append(label);
    }
  });
  figure.append(caption, svg); grid.append(figure); return true;
}

export function makeReportCharts(scriptsReport, listing) {
  const charts = scriptsReport?.charts || {}; const finance = Array.isArray(listing?.monthly_financials) ? listing.monthly_financials : [];
  const section = document.createElement('section'); section.className = 'analysis-block report-section report-charts';
  const heading = document.createElement('h2'); heading.className = 'section-title'; heading.textContent = 'Итоговые графики аналитики';
  const grid = document.createElement('div'); grid.className = 'report-chart-grid'; let count = 0;
  count += Number(addLineChart(grid, 'Выручка по месяцам', charts.revenue_line?.length ? charts.revenue_line : finance.map((row) => ({ month: row.month, value: row.revenue }))));
  count += Number(addLineChart(grid, 'Чистая прибыль по месяцам', charts.profit_line?.length ? charts.profit_line : finance.map((row) => ({ month: row.month, value: row.net_profit })), 'moderation-chart--profit'));
  count += Number(addLineChart(grid, 'Сезонность', charts.seasonality_bar || [], 'moderation-chart--seasonality'));
  if (Array.isArray(charts.expenses_pie) && charts.expenses_pie.length) {
    const panel = document.createElement('article'); panel.className = 'expense-chart';
    const title = document.createElement('h3'); title.textContent = 'Структура расходов'; panel.append(title);
    const total = charts.expenses_pie.reduce((sum, item) => sum + (Number(item.value) || 0), 0);
    charts.expenses_pie.forEach((item) => {
      const row = document.createElement('div'); row.className = 'expense-chart__row';
      const label = document.createElement('span'); label.textContent = labelFor(item.name || 'expense');
      const track = document.createElement('span'); track.className = 'expense-chart__track';
      const bar = document.createElement('span'); bar.className = 'expense-chart__bar';
      bar.style.width = `${total > 0 ? Math.max(0, Math.min(100, Number(item.value) / total * 100)) : 0}%`; track.append(bar);
      const value = document.createElement('strong'); value.textContent = `${moneyFormat.format(Number(item.value) || 0)} ₽`;
      row.append(label, track, value); panel.append(row);
    });
    grid.append(panel); count += 1;
  }
  if (!count) return null;
  section.append(heading, grid); return section;
}