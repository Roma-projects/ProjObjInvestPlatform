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
  forecast_commentary: 'Пояснение к прогнозу', expected_monthly_profit: 'Ожидаемая прибыль в месяц',
  expected_monthly_revenue: 'Ожидаемая выручка в месяц', risk_rating: 'Уровень риска', photo_issues: 'Замечания к фото',
  critical_flags: 'Критические замечания', verification_summary: 'Сводка проверок', registry_status: 'Статус реестра',
  documents_missing: 'Не представлены документы', documents_provided: 'Представленные документы',
  price_status: 'Оценка цены', fair_price_min: 'Минимальная ориентировочная стоимость',
  fair_price_max: 'Максимальная ориентировочная стоимость', valuation_commentary: 'Пояснение к оценке',
  price_deviation_percent: 'Отклонение цены', recommendation: 'Рекомендация',
  status: 'Статус', extract: 'Найденные сведения', identity_check: 'Сверка данных продавца',
  fio_match: 'Совпадение ФИО', inn_match: 'Совпадение ИНН', business_status_match: 'Статус ИП подтверждён',
  document_downloaded: 'Выписка загружена', verified: 'Проверка подтверждена',
  uploaded: 'Загружен', readable: 'Читается', source_text_excerpt: 'Сведения из источника',
  sources_checked: 'Проверенные источники', failed_sources: 'Источники с ошибкой', total_duration_ms: 'Время проверки, мс',
  registration_date: 'Дата регистрации', okved: 'Коды деятельности', bankruptcy_proceedings: 'Сведения о банкротстве',
  arbitration_cases: 'Арбитражные дела', region: 'Регион регистрации', document_downloaded: 'Выписка загружена',
  none: 'Не выявлено', allowed: 'Разрешено', review: 'Нужна проверка', suspicious: 'Подозрительно',
  blocked: 'Заблокировано', prohibited: 'Запрещено', low: 'Низкий', moderate: 'Средний', high: 'Высокий',
  critical: 'Критический', stable: 'Стабильная', growth: 'Рост', decline: 'Снижение', seasonal: 'Сезонная',
  unknown: 'Недостаточно данных', verified: 'Подтверждён', unverified: 'Не подтверждён',
  skipped: 'Не запускалась', not_applicable: 'Не применяется', awaiting: 'Выполняется', timeout: 'Истекло время ожидания',
  error: 'Ошибка проверки', partial: 'Проверена частично', not_found: 'Запись не найдена', ok: 'Пройдена', warning: 'Предупреждение',
  requires_moderation: 'Нужна модерация', auto_ok: 'Автоматически одобрено', needs_human_review: 'Нужна ручная оценка',
  significantly_overpriced: 'Цена значительно выше ориентировочной', overpriced: 'Цена выше ориентировочной',
  fair: 'Цена в пределах ориентира', underpriced: 'Цена ниже ориентира',
};

const moneyFormat = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const labelFor = (key) => labels[key] || String(key).replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const moneyLike = /(price|revenue|profit|expense|value|salary|debt|assets|rent|check)/i;
const hiddenFields = /(^|_)(id|path|url|filename|file|files|directory|folder|token|source_text_excerpt|photos|main_photo|floor_plan_image|video|created_at|updated_at)$/i;

Object.assign(labels, {
  comment: 'Комментарий', confidence: 'Уверенность', confidence_level: 'Уровень уверенности',
  employee_count: 'Количество сотрудников', annual_revenue: 'Годовая выручка',
  rent: 'Аренда', payroll: 'Заработная плата', purchases: 'Закупки', utilities: 'Коммунальные услуги',
  taxes: 'Налоги', marketing: 'Маркетинг', other: 'Прочие расходы',
  profitability_percent_by_month: 'Рентабельность по месяцам', expense_structure_percent: 'Структура расходов, %',
  average_profitability_percent: 'Средняя рентабельность', debt_load_months: 'Кредитная нагрузка, месяцев',
  rent_per_sqm: 'Аренда за м²', revenue_per_employee: 'Выручка на сотрудника', assets_value: 'Стоимость активов',
  business_type: 'Тип бизнеса', property_type: 'Тип помещения', property_condition: 'Состояние помещения',
  deal_composition: 'Состав сделки', transfer_method: 'Способ передачи', business_age_months: 'Возраст бизнеса, месяцев',
  area_sqm: 'Площадь, м²', sale_price: 'Цена продажи', stock_value: 'Стоимость товарного остатка',
  average_check: 'Средний чек', monthly_orders: 'Количество заказов в месяц', monthly_clients_unique: 'Уникальных клиентов в месяц',
  repeat_customer_rate: 'Доля повторных клиентов', customer_base_size: 'Размер клиентской базы',
  debts_receivable: 'Дебиторская задолженность', debts_payable: 'Кредиторская задолженность',
  monthly_loan_payments: 'Платежи по кредитам в месяц', staff_count: 'Количество сотрудников',
  equipment_list: 'Оборудование', staff_details: 'Состав команды', business_name: 'Название бизнеса',
  short_description: 'Краткое описание', full_description: 'Полное описание', seller_name: 'Продавец',
  seller_status: 'Статус продавца', seller_inn: 'ИНН', seller_ogrnip: 'ОГРНИП', country: 'Страна', city: 'Город',
  street: 'Улица', house: 'Дом', seasonality_months: 'Сезонные месяцы', supplier_contracts: 'Договоры с поставщиками',
  supplier_details: 'Поставщики', legal_claims: 'Судебные споры', legal_claims_details: 'Детали судебных споров',
  equipment_lease: 'Аренда оборудования', stock_included: 'Товарный остаток включён', has_licenses: 'Лицензии',
  has_contracts: 'Договоры', sale_reason: 'Причина продажи', has_documents: 'Наличие документов',
  revenue: 'Выручка', net_profit: 'Чистая прибыль', total_expenses: 'Общие расходы', rent_expenses: 'Расходы на аренду',
  payroll_expenses: 'Расходы на зарплату', purchases_expenses: 'Расходы на закупки', utilities_expenses: 'Расходы на коммунальные услуги',
  taxes_expenses: 'Расходы на налоги', marketing_expenses: 'Расходы на маркетинг', other_expenses: 'Прочие расходы',
  month: 'Месяц', equipment_value: 'Стоимость оборудования', salary: 'Заработная плата', count: 'Количество',
  verification_level: 'Уровень проверки', expected_ogrnip_match: 'ОГРНИП совпадает',
  code: 'Код', name: 'Показатель', value: 'Значение', month: 'Месяц',
  self_employed: 'Самозанятый', ip: 'Индивидуальный предприниматель', legal_entity: 'Юридическое лицо', individual: 'Физическое лицо',
  full_transfer_training: 'Полная передача с обучением', owner: 'Собственник', free_purpose: 'Свободное назначение',
  good_condition: 'Хорошее состояние', food: 'Общественное питание',
});

function cleanReportData(value) {
  if (typeof value === 'string' && (/^https?:\/\//i.test(value) || /(?:^|\/)public\/uploads\/|\.(?:pdf|png|jpe?g|webp|docx?|xlsx?)(?:$|[?#])/i.test(value))) return null;
  if (Array.isArray(value)) return value.map(cleanReportData).filter((item) => item !== null);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !hiddenFields.test(key) && !['source_text_excerpt', 'registry_extract'].includes(key))
    .map(([key, nested]) => [key, cleanReportData(nested)]));
}

function formatValue(key, value) {
  if (value === null || value === undefined || value === '') return 'Не указано';
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет';
  if (typeof value === 'number') {
    if (/(percent|rate|confidence)$/i.test(key)) return `${(Math.abs(value) <= 1 && value !== 0 ? value * 100 : value).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`;
    if (moneyLike.test(key)) return `${moneyFormat.format(value)} ₽`;
    return value.toLocaleString('ru-RU', { maximumFractionDigits: 2 });
  }
  if (typeof value === 'string') return labels[value] || value.replaceAll('_', ' ');
  return '';
}

function addData(grid, data, columns = 3) {
  let added = 0;
  Object.entries(data || {}).forEach(([key, value]) => {
    if (value === undefined || hiddenFields.test(key)
      || ['source_text_excerpt', 'registry_extract', 'extract'].includes(key)) return;
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
            ? Object.entries(cleanReportData(entry)).map(([field, detail]) => `${labelFor(field)}: ${formatValue(field, detail)}`).filter((text) => !text.endsWith(': Не указано')).join(' · ') || 'Нет данных'
            : formatValue(key, entry);
          list.append(row);
        });
        content.append(list);
      }
    } else if (value && typeof value === 'object') {
      card.classList.add('report-value--nested');
      const nested = document.createElement('div'); nested.className = 'report-value__nested';
      addData(nested, cleanReportData(value), 2); content.append(nested);
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
  if (!addData(grid, cleanReportData(data))) return null;
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
  const width = 1000; const height = 360; const pad = { top: 28, right: 28, bottom: 48, left: 100 };
  const rawMin = Math.min(0, ...values.map((point) => point.value)); const rawMax = Math.max(0, ...values.map((point) => point.value));
  const spanRaw = rawMax - rawMin || 1; const min = rawMin - spanRaw * 0.08; const max = rawMax + spanRaw * 0.08;
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
    const tick = document.createElementNS(svg.namespaceURI, 'text');
    tick.setAttribute('x', String(pad.left - 12)); tick.setAttribute('y', String(y + 5));
    tick.setAttribute('text-anchor', 'end'); tick.setAttribute('class', 'moderation-chart__label');
    tick.textContent = Math.round(max - span * fraction).toLocaleString('ru-RU'); svg.append(tick);
  });
  const polyline = document.createElementNS(svg.namespaceURI, 'polyline');
  polyline.setAttribute('points', coords.map((p) => `${p.x},${p.y}`).join(' ')); polyline.setAttribute('class', 'moderation-chart__line'); svg.append(polyline);
  coords.forEach((point, index) => {
    const circle = document.createElementNS(svg.namespaceURI, 'circle'); circle.setAttribute('cx', String(point.x));
    circle.setAttribute('cy', String(point.y)); circle.setAttribute('r', '6'); circle.setAttribute('class', 'moderation-chart__point');
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
  const number = (value) => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') return Number(value.replace(/\s/g, '').replace(',', '.'));
    return NaN;
  };
  const financePoints = (key) => finance.map((row) => ({ month: row.month, value: number(row[key]) }));
  const usefulPoints = (points) => Array.isArray(points) && points.some((point) => Number(point?.value ?? point?.index) !== 0);
  const revenuePoints = usefulPoints(charts.revenue_line) ? charts.revenue_line : financePoints('revenue');
  const profitPoints = usefulPoints(charts.profit_line) ? charts.profit_line : financePoints('net_profit');
  const seasonalityPoints = usefulPoints(charts.seasonality_bar) ? charts.seasonality_bar : (() => {
    const revenues = finance.map((row) => number(row.revenue) || 0);
    const average = revenues.length ? revenues.reduce((sum, value) => sum + value, 0) / revenues.length : 0;
    return finance.map((row) => ({ month: row.month, index: average ? (number(row.revenue) || 0) / average : null }));
  })();
  count += Number(addLineChart(grid, 'Выручка по месяцам · ₽', revenuePoints));
  count += Number(addLineChart(grid, 'Чистая прибыль по месяцам · ₽', profitPoints, 'moderation-chart--profit'));
  count += Number(addLineChart(grid, 'Сезонность · индекс к средней выручке', seasonalityPoints, 'moderation-chart--seasonality'));
  const expenseKeys = ['rent_expenses', 'payroll_expenses', 'purchases_expenses', 'utilities_expenses', 'taxes_expenses', 'marketing_expenses', 'other_expenses'];
  const chartExpenses = Array.isArray(charts.expenses_pie) ? charts.expenses_pie : [];
  const expenseData = chartExpenses.some((item) => Number(item.value) > 0)
    ? chartExpenses
    : expenseKeys.map((key) => ({ name: key.replace('_expenses', ''), value: finance.reduce((sum, row) => sum + (number(row[key]) || 0), 0) }));
  if (expenseData.some((item) => Number(item.value) > 0)) {
    const panel = document.createElement('article'); panel.className = 'expense-chart';
    const title = document.createElement('h3'); title.textContent = 'Структура расходов'; panel.append(title);
    const total = expenseData.reduce((sum, item) => sum + (Number(item.value) || 0), 0);
    expenseData.filter((item) => Number(item.value) > 0).forEach((item) => {
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