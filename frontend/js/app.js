import {
  login,
  me,
  register,
  requestPasswordReset,
  resendVerificationCode,
  resetPassword,
  updateProfile,
  verifyEmail,
  logout,
} from '../src/services/auth.js';
import { restoreSession, getAccessToken, setAccessToken } from '../src/services/api.js';
import {
  createListing,
  getListing,
  getListings,
  submitListing,
  updateListing,
  uploadListingFile,
} from '../src/services/listings.js';
import {
  addToBlacklist,
  decideModerationCase,
  getBlacklist,
  getModerationCase,
  getModerationCases,
  openModerationDocument,
  removeFromBlacklist,
  removeFromCatalog,
} from '../src/services/moderation.js';
import { getPublishedListing, search, searchMap } from '../src/services/search.js';
import {
  createConversation,
  getConversation,
  getConversations,
  markMessagesRead,
  sendMessage,
  connectNotifications,
} from '../src/services/chat.js';

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const currency = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
let loadedUser = null;
let currentCatalogFilters = {};
let catalogCursor = null;
let catalogItems = [];
let catalogTemplate = null;
let catalogLeafletMap = null;
let catalogMarkerLayer = null;
let selectedMapMarker = null;
let selectedMapListingId = null;

function notify(message, kind = 'info') {
  let toast = $('.miero-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'miero-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.append(toast);
  }
  toast.textContent = message;
  toast.classList.toggle('miero-toast--error', kind === 'error');
  clearTimeout(notify.timeout);
  notify.timeout = setTimeout(() => toast.remove(), 5200);
}

function emptyState(text, linkLabel, linkHref) {
  const box = document.createElement('div');
  box.className = 'miero-empty';
  box.textContent = text;
  if (linkLabel && linkHref) {
    box.append(' ');
    const link = document.createElement('a');
    link.href = linkHref;
    link.textContent = linkLabel;
    box.append(link);
  }
  return box;
}

function asItems(response) {
  if (Array.isArray(response)) return response;
  return Array.isArray(response?.items) ? response.items : [];
}

function formatMoney(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${currency.format(number)} ₽` : 'Цена не указана';
}

function safeInternalDestination(value, fallback = 'profile.html') {
  try {
    const target = new URL(value || fallback, location.href);
    const appRoot = new URL('.', location.href).pathname;
    if (target.origin !== location.origin || !target.pathname.startsWith(appRoot)) return fallback;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return fallback;
  }
}

function localizedStatus(status) {
  return ({
    draft: 'Черновик',
    processing: 'Идёт проверка',
    on_moderation: 'На модерации',
    published: 'Опубликовано',
    removed: 'Снято модератором',
    blocked: 'Заблокировано',
    rejected: 'Отклонено',
  })[status] || status || '—';
}

function listingIdFromHash() {
  try { return decodeURIComponent(location.hash.slice(1)); } catch { return ''; }
}

function placeImage(element, url) {
  if (!element) return;
  if (!url) {
    element.style.backgroundImage = '';
    element.classList.add('placeholder');
    return;
  }
  element.classList.remove('placeholder');
  element.style.backgroundImage = `url("${String(url).replaceAll('"', '%22')}")`;
  element.style.backgroundPosition = 'center';
  element.style.backgroundSize = 'cover';
}

function updateIconFavorite(button, active) {
  button.classList.toggle('is-active', active);
  button.setAttribute('aria-pressed', String(active));
  button.setAttribute('aria-label', active ? 'Убрать из избранного' : 'Добавить в избранное');
  const image = $('img', button);
  if (image) image.src = active ? '/assets/icons/heart-filled.svg' : '/assets/icons/heart.svg';
}

function favoriteIds() {
  try {
    const values = JSON.parse(localStorage.getItem('mieroventure.favorites') || '[]');
    return Array.isArray(values) ? values.map(String) : [];
  } catch {
    return [];
  }
}

function saveFavorite(id, active) {
  if (!id) return false;
  const values = new Set(favoriteIds());
  if (active) values.add(String(id));
  else values.delete(String(id));
  try { localStorage.setItem('mieroventure.favorites', JSON.stringify([...values])); } catch { /* storage can be disabled */ }
  return true;
}

function setIconText(item, text) {
  if (!item) return;
  const textNode = [...item.childNodes].reverse().find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
  if (textNode) textNode.textContent = ` ${text}`;
  else item.append(document.createTextNode(text));
}

function setCardDetails(card, item) {
  const id = item.listing_id || item.id;
  card.dataset.listingId = id || '';
  $('.card__title', card)?.replaceChildren(document.createTextNode(item.business_name || 'Бизнес на продаже'));
  $('.card__price', card)?.replaceChildren(document.createTextNode(formatMoney(item.sale_price)));
  const meta = $$('.card__meta li', card);
  setIconText(meta[0], item.verification_status === 'deep' ? 'Глубокая проверка' : 'Базовая проверка');
  setIconText(meta[1], item.location?.city || 'Город не указан');
  setIconText(meta[2], displayEnum(item.business_type) || 'Другое');
  const more = $('.card__more', card);
  if (more && id) more.href = `listing.html#${encodeURIComponent(id)}`;
  const image = item.main_photo || item.photos?.[0];
  placeImage($('.card__image', card), image);
  const favorite = $('.card__fav', card);
  if (favorite) {
    const active = favoriteIds().includes(String(id));
    updateIconFavorite(favorite, active);
  }
}

function collectCatalogFilters(form) {
  const val = (name) => form.elements.namedItem(name)?.value?.trim() || '';
  const checked = (name) => $$(`[name="${name}"]:checked`, form).map((input) => input.value).filter((value) => value && value !== 'all');
  const numberOrUndefined = (value) => value ? Number(value.replace(/\s/g, '').replace(',', '.')) : undefined;
  const types = checked('business_type');
  const deals = checked('deal_composition');
  const properties = checked('property_type');
  const conditions = checked('condition');
  const transfers = checked('transfer_method');
  const trends = checked('revenue_trend');
  const category = $$('[name="sort_category"]:checked', form)[0]?.value;
  const priceSort = $$('[name="sort_price"]:checked', form)[0]?.value;
  const sort = priceSort === 'asc' ? 'price_asc' : priceSort === 'desc' ? 'price_desc' : 'newest';
  const filters = {
    q: val('q') || undefined,
    business_type: types.length ? types : undefined,
    deal_composition: deals.length ? deals : undefined,
    property_type: properties.length ? properties : undefined,
    property_condition: conditions.length ? conditions : undefined,
    transfer_method: transfers.length ? transfers : undefined,
    revenue_trend: trends.length ? trends : undefined,
    min_price: numberOrUndefined(val('price_from')),
    max_price: numberOrUndefined(val('price_to')),
    city: val('city') || undefined,
    verification_status: category && category !== 'all' ? category : undefined,
    sort,
    limit: 20,
  };
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined && value !== ''));
}

async function loadCatalog(form, append = false) {
  const container = $('.cards');
  if (!container) return;
  catalogTemplate ||= $('.card', container)?.cloneNode(true) || null;
  if (!append) {
    currentCatalogFilters = collectCatalogFilters(form);
    catalogCursor = null;
    catalogItems = [];
    container.replaceChildren(emptyState('Загрузка каталога…'));
  }
  const payload = { ...currentCatalogFilters, ...(append && catalogCursor ? { cursor: catalogCursor } : {}) };
  container.classList.add('miero-loading');
  try {
    const result = await search(payload);
    if (!append) await loadCatalogMap(currentCatalogFilters, true);
    const items = asItems(result);
    catalogCursor = result?.next_cursor || null;
    catalogItems = append ? [...catalogItems, ...items] : items;
    const template = catalogTemplate;
    if (!append) container.replaceChildren();
    if (!items.length && !append) {
      container.append(emptyState('По этим фильтрам бизнес не найден. Измените параметры поиска.'));
    } else if (template) {
      items.forEach((item) => {
        const card = template.cloneNode(true);
        setCardDetails(card, item);
        container.append(card);
      });
    }
    let more = $('.miero-load-more');
    if (catalogCursor) {
      if (!more) {
        more = document.createElement('button');
        more.className = 'miero-load-more';
        more.type = 'button';
        more.textContent = 'Показать ещё';
        container.after(more);
        more.addEventListener('click', () => loadCatalog(form, true));
      }
      more.hidden = false;
    } else if (more) {
      more.hidden = true;
    }
  } catch (error) {
    container.replaceChildren(emptyState(`Не удалось загрузить каталог: ${error.message}`));
    notify(error.message, 'error');
  } finally {
    container.classList.remove('miero-loading');
  }
}

function addOpenStreetMapTiles(map) {
  const template = $('meta[name="miero-map-tiles"]')?.content
    || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  window.L.tileLayer(template, {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
  }).addTo(map);
}

function selectCatalogMapItem(item, marker) {
  if (selectedMapMarker && selectedMapMarker !== marker) {
    selectedMapMarker.setStyle({ color: '#ffffff', weight: 2, fillColor: '#680A18', fillOpacity: 0.92 });
  }
  selectedMapMarker = marker;
  selectedMapListingId = String(item.listing_id);
  marker.setStyle({ color: '#680A18', weight: 3, fillColor: '#D9C6A5', fillOpacity: 1 });
  const panel = $('#catalog-map-selection');
  const hint = $('.catalog-map__hint', panel);
  const title = $('.catalog-map__selected-title', panel);
  const price = $('.catalog-map__selected-price', panel);
  const city = $('.catalog-map__selected-city', panel);
  const details = $('#catalog-map-details');
  if (hint) hint.hidden = true;
  if (title) { title.hidden = false; title.textContent = item.business_name || 'Бизнес на продаже'; }
  if (price) {
    price.hidden = false;
    price.textContent = item.sale_price === null || item.sale_price === undefined ? 'Цена не указана' : formatMoney(item.sale_price);
  }
  if (city) {
    city.hidden = !item.city;
    city.textContent = item.city
      ? `${item.city}${item.coordinate_precision === 'city' ? ' · приблизительная точка' : ''}`
      : (item.coordinate_precision === 'city' ? 'Приблизительная точка: центр города' : '');
    city.hidden = !city.textContent;
  }
  if (details) details.hidden = false;
}

async function openListingFromMap() {
  if (!selectedMapListingId) return;
  const destination = `listing.html#${encodeURIComponent(selectedMapListingId)}`;
  if (getAccessToken()) {
    try {
      await me();
      location.href = destination;
      return;
    } catch {
      setAccessToken(null);
    }
  }
  const authenticated = await restoreSession().catch(() => false);
  if (authenticated) {
    try {
      await me();
      location.href = destination;
      return;
    } catch {
      setAccessToken(null);
    }
  }
  sessionStorage.setItem('mieroventure.redirect', destination);
  location.href = 'login.html';
}

async function loadCatalogMap(filters = {}, fitMap = false) {
  const canvas = $('#catalog-map-canvas');
  if (!canvas) return;
  const status = $('#catalog-map-status');
  const count = $('#catalog-map-count');
  if (!window.L) {
    if (status) status.textContent = 'Не удалось загрузить библиотеку карты. Обновите страницу позже.';
    return;
  }
  if (!catalogLeafletMap) {
    catalogLeafletMap = window.L.map(canvas, { scrollWheelZoom: false }).setView([61, 90], 3);
    addOpenStreetMapTiles(catalogLeafletMap);
    catalogMarkerLayer = window.L.layerGroup().addTo(catalogLeafletMap);
    $('#catalog-map-details')?.addEventListener('click', openListingFromMap);
    requestAnimationFrame(() => catalogLeafletMap?.invalidateSize());
  }
  if (status) status.textContent = 'Загружаем объявления…';
  try {
    const result = await searchMap(filters);
    const items = asItems(result);
    catalogMarkerLayer.clearLayers();
    selectedMapMarker = null;
    selectedMapListingId = null;
    const hint = $('.catalog-map__hint');
    const title = $('.catalog-map__selected-title');
    const price = $('.catalog-map__selected-price');
    const city = $('.catalog-map__selected-city');
    const details = $('#catalog-map-details');
    if (hint) hint.hidden = false;
    [title, price, city].forEach((node) => { if (node) { node.hidden = true; node.textContent = ''; } });
    if (details) details.hidden = true;
    const points = [];
    items.forEach((item) => {
      const latitude = Number(item.latitude);
      const longitude = Number(item.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
      const marker = window.L.circleMarker([latitude, longitude], {
        radius: 8,
        color: '#ffffff',
        weight: 2,
        fillColor: '#680A18',
        fillOpacity: 0.92,
        className: 'miero-map-marker',
      });
      marker.on('click', () => selectCatalogMapItem(item, marker));
      marker.addTo(catalogMarkerLayer);
      points.push([latitude, longitude]);
    });
    if (count) count.textContent = `${result.total ?? items.length} на карте`;
    if (status) {
      const messages = [];
      if (result.unlocated) messages.push(`${result.unlocated} объявл. без координат`);
      if (result.truncated) messages.push('показана первая часть объектов — уточните фильтры');
      status.textContent = messages.join(' · ');
    }
    if (points.length && fitMap) {
      if (points.length === 1) catalogLeafletMap.setView(points[0], items[0]?.coordinate_precision === 'city' ? 11 : 13);
      else catalogLeafletMap.fitBounds(points, { padding: [24, 24], maxZoom: 13 });
    }
    requestAnimationFrame(() => catalogLeafletMap?.invalidateSize());
  } catch (error) {
    if (status) status.textContent = `Карта временно недоступна: ${error.message}`;
  }
}

function bindCatalog() {
  const form = $('.catalog-form');
  if (!form) return;
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    loadCatalog(form);
  });
  form.addEventListener('reset', () => setTimeout(() => loadCatalog(form), 0));
  if (location.pathname.endsWith('/catalog.html')) loadCatalog(form);
}

function listingCardFrom(item, template, favoriteMode = false) {
  const card = template.cloneNode(true);
  const id = item.listing_id || item.id;
  card.dataset.listingId = id || '';
  $('.listing__title', card)?.replaceChildren(document.createTextNode(item.business_name || 'Бизнес на продаже'));
  $('.listing__price', card)?.replaceChildren(document.createTextNode(formatMoney(item.sale_price)));
  $('.listing__desc-text', card)?.replaceChildren(document.createTextNode(item.short_description || 'Описание не заполнено'));
  const meta = $$('.listing__meta li', card);
  setIconText(meta[0], item.location?.city || item.city || 'Город не указан');
  setIconText(meta[1], displayEnum(item.business_type) || 'Другое');
  placeImage($('.listing__image', card), item.main_photo || item.files?.main_photo || item.photos?.[0]);
  const check = $('.listing__check', card);
  if (check) {
    if (item.verification_status === 'deep') check.textContent = 'Глубокая проверка';
    else if (item.verification_status === 'basic') check.textContent = 'Базовая проверка';
    else check.hidden = true;
  }
  const status = $('.status', card);
  if (status) status.textContent = localizedStatus(item.status);
  const date = $('.listing__date', card);
  if (date) date.textContent = item.created_at ? `Создано: ${new Date(item.created_at).toLocaleDateString('ru-RU')}` : '';
  const moreLink = $('.listing__title a', card) || $('.listing__main', card);
  if (moreLink && id) moreLink.dataset.href = `listing.html#${encodeURIComponent(id)}`;
  card.addEventListener('click', (event) => {
    if (event.target.closest('button, a')) return;
    if (card.dataset.href) location.href = card.dataset.href;
    else if (id) location.href = `listing.html#${encodeURIComponent(id)}`;
  });
  const favorite = $('.listing__fav', card);
  if (favorite) {
    updateIconFavorite(favorite, favoriteMode || favoriteIds().includes(String(id)));
    favorite.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const active = !favoriteIds().includes(String(id));
      saveFavorite(id, active);
      updateIconFavorite(favorite, active);
      if (favoriteMode && !active) card.remove();
    });
  }
  $('.listing__menu', card)?.setAttribute('hidden', '');
  return card;
}

async function loadFavorites() {
  const container = $('.listings');
  const ids = favoriteIds();
  const template = $('.listing', container || document);
  if (!container || !template) return;
  container.replaceChildren();
  if (!ids.length) {
    container.append(emptyState('В избранном пока нет объявлений.', 'Открыть каталог', 'catalog.html'));
    return;
  }
  try {
    const rows = await Promise.all(ids.map((id) => getPublishedListing(id).catch(() => null)));
    const found = rows.filter(Boolean);
    if (!found.length) {
      container.append(emptyState('Сохранённые объявления больше не доступны.', 'Открыть каталог', 'catalog.html'));
      return;
    }
    found.forEach((item) => container.append(listingCardFrom(item, template, true)));
  } catch (error) {
    container.append(emptyState(`Не удалось загрузить избранное: ${error.message}`));
  }
}

async function loadOwnListings() {
  const container = $('.my-listings .listings') || $('.profile .listings');
  if (!container) return [];
  const template = $('.listing', container);
  container.replaceChildren(emptyState('Загрузка объявлений…'));
  try {
    const result = await getListings();
    const items = asItems(result);
    container.replaceChildren();
    if (!items.length) {
      container.append(emptyState('У вас пока нет объявлений.', 'Разместить объявление', 'create-listing.html'));
      return [];
    }
    items.forEach((item) => {
      const card = listingCardFrom(item, template || document.createElement('article'));
      const status = item.status || 'draft';
      card.classList.remove('listing--active', 'listing--moderation', 'listing--archive');
      card.classList.add(status === 'published' ? 'listing--active' : status === 'on_moderation' || status === 'processing' ? 'listing--moderation' : 'listing--archive');
      card.dataset.status = status;
      if (status === 'draft') card.dataset.href = `create-listing.html#${encodeURIComponent(item.id)}`;
      if (template && $('.listing__aside .listing__top', card)) {
        let badge = $('.status', card);
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'status';
          $('.listing__aside .listing__top', card).prepend(badge);
        }
        badge.textContent = localizedStatus(status);
      }
      if (template) container.append(card);
    });
    const inputs = $$('[name="listing-status"]');
    const applyStatusFilter = () => {
      const checked = inputs.find((input) => input.checked);
      const filter = checked?.id || 'l-all';
      $$('.listing', container).forEach((card) => {
        const status = card.dataset.status;
        card.hidden = filter === 'l-moderation' ? !['on_moderation', 'processing'].includes(status)
          : filter === 'l-active' ? status !== 'published'
            : filter === 'l-archive' ? !['rejected', 'withdrawn'].includes(status)
              : false;
      });
    };
    inputs.forEach((input) => input.addEventListener('change', applyStatusFilter));
    applyStatusFilter();
    return items;
  } catch (error) {
    container.replaceChildren(emptyState(`Не удалось загрузить объявления: ${error.message}`, 'Войти', 'login.html'));
    notify(error.message, 'error');
    return [];
  }
}

function registerAuthForms() {
  const loginForm = $('.login__form');
  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(loginForm);
    const button = $('button[type="submit"]', loginForm);
    if (button) button.disabled = true;
    try {
      await login(String(form.get('login') || '').trim(), String(form.get('password') || ''));
      const destination = safeInternalDestination(sessionStorage.getItem('mieroventure.redirect'), 'profile.html');
      sessionStorage.removeItem('mieroventure.redirect');
      location.href = destination;
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      if (button) button.disabled = false;
    }
  });

  const registrationForm = $('.registration__form');
  registrationForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = new FormData(registrationForm);
    const password = String(values.get('password') || '');
    if (password.length < 12) return notify('Пароль должен содержать не менее 12 символов.', 'error');
    if (password !== values.get('password_confirmation')) return notify('Пароли не совпадают.', 'error');
    if (!values.get('agreement')) return notify('Подтвердите согласие с условиями.', 'error');
    try {
      await register({
        first_name: String(values.get('first_name') || '').trim(),
        last_name: String(values.get('last_name') || '').trim(),
        patronymic: String(values.get('middle_name') || '').trim() || null,
        phone: String(values.get('phone') || '').trim(),
        email: String(values.get('email') || '').trim(),
        password,
        password_confirm: String(values.get('password_confirmation') || ''),
        agree_to_terms: true,
      });
      sessionStorage.setItem('mieroventure.registration_email', String(values.get('email') || ''));
      location.href = 'email-confirmation.html';
    } catch (error) {
      notify(error.message, 'error');
    }
  });

  const verifyForm = $('.email-confirmation__form');
  verifyForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const code = String(new FormData(verifyForm).get('verification_code') || '').trim();
    try {
      await verifyEmail(code);
      notify('Почта подтверждена. Теперь войдите в аккаунт.');
      location.href = 'login.html';
    } catch (error) {
      notify(error.message, 'error');
    }
  });
  $('.email-confirmation__resend-button')?.addEventListener('click', async () => {
    try {
      await resendVerificationCode();
      notify('Если подтверждение требуется, новый код отправлен на почту.');
    } catch (error) {
      notify(error.message, 'error');
    }
  });

  const recoveryForm = $('.password-recovery__form');
  recoveryForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const resetPanel = $('.password-recovery__reset', recoveryForm);
    if (!resetPanel || resetPanel.hidden) {
      const address = String(new FormData(recoveryForm).get('login') || '').trim();
      try {
        await requestPasswordReset(address);
        resetPanel.hidden = false;
        const button = $('button[type="submit"]', recoveryForm);
        if (button) button.textContent = 'Сменить пароль';
        notify('Если адрес зарегистрирован, инструкция отправлена на почту.');
      } catch (error) {
        notify(error.message, 'error');
      }
      return;
    }
    const values = new FormData(recoveryForm);
    const password = String(values.get('new_password') || '');
    if (password !== values.get('new_password_confirm')) return notify('Пароли не совпадают.', 'error');
    try {
      await resetPassword({
        token_from_email: String(values.get('token_from_email') || '').trim(),
        new_password: password,
        new_password_confirm: String(values.get('new_password_confirm') || ''),
      });
      notify('Пароль изменён. Войдите с новым паролем.');
      location.href = 'login.html';
    } catch (error) {
      notify(error.message, 'error');
    }
  });
}

function formControls(root) {
  return root?.elements ? [...root.elements] : $$('input, select, textarea', root || document);
}

function formNumber(form, name, root = form) {
  const field = formControls(root).find((element) => element.name === name);
  if (!field || !String(field.value).trim()) return undefined;
  const value = Number(String(field.value).trim().replace(/\s/g, '').replace(',', '.'));
  return Number.isFinite(value) ? value : undefined;
}

function formValue(form, name, root = form) {
  const controls = formControls(root).filter((element) => element.name === name);
  const selected = controls.find((element) => (element.type !== 'radio' && element.type !== 'checkbox') || element.checked);
  return selected ? String(selected.value || '').trim() : '';
}

function formBoolean(form, name) {
  const value = formValue(form, name);
  return value === 'yes' ? true : value === 'no' ? false : undefined;
}

function draftFromForm(form) {
  const choice = (name) => {
    const value = formValue(form, name);
    return value && value !== 'all' ? value : undefined;
  };
  const type = choice('property_type');
  const hours = [formValue(form, 'work_from'), formValue(form, 'work_to')].filter(Boolean).join('–');
  const details = {};
  const numberAt = (root, name) => formNumber(form, name, root);
  const valueAt = (root, name) => formValue(form, name, root);
  const equipment = $$('[data-repeat="equipment"]', form).map((root, index) => {
    const name = valueAt(root, 'equipment_name[]');
    if (!name) return null;
    const condition = valueAt(root, `equipment_condition_${index + 1}`);
    const conditionMap = { excellent: 'отличное', good: 'хорошее', repair: 'требует замены/ремонта' };
    return {
      equipment_name: name,
      equipment_brand: valueAt(root, 'equipment_brand[]') || null,
      equipment_condition: conditionMap[condition] || condition || null,
      equipment_purchase_year: numberAt(root, 'equipment_year[]'),
      equipment_value: numberAt(root, 'equipment_price[]'),
    };
  }).filter(Boolean);
  const staff = $$('[data-repeat="staff"]', form).map((root) => ({
    position: valueAt(root, 'staff_position[]'),
    count: numberAt(root, 'staff_count[]'),
    salary: numberAt(root, 'staff_salary[]'),
  })).filter((item) => item.position && item.count !== undefined && item.salary !== undefined);
  const financials = $$('[data-repeat="month"]', form).map((root) => {
    const monthInput = $$('[name^="month_"]:checked', root)[0];
    if (!monthInput) return null;
    const month = String(monthInput.value).padStart(2, '0');
    const revenue = numberAt(root, 'revenue[]') ?? 0;
    const totalExpenses = numberAt(root, 'costs_total[]') ?? 0;
    return {
      month: `${new Date().getFullYear()}-${month}`,
      revenue,
      total_expenses: totalExpenses,
      utilities_expenses: numberAt(root, 'costs_utilities[]') ?? 0,
      rent_expenses: numberAt(root, 'costs_rent[]') ?? 0,
      payroll_expenses: numberAt(root, 'costs_payroll[]') ?? 0,
      purchases_expenses: numberAt(root, 'costs_purchases[]') ?? 0,
      taxes_expenses: numberAt(root, 'costs_taxes[]') ?? 0,
      marketing_expenses: numberAt(root, 'costs_marketing[]') ?? 0,
      other_expenses: numberAt(root, 'costs_other[]') ?? 0,
      net_profit: numberAt(root, 'net_profit[]') ?? revenue - totalExpenses,
    };
  }).filter(Boolean);
  const splitNumbers = (value) => value.split(/[\s,;]+/).filter(Boolean).map(Number).filter((item) => Number.isInteger(item) && item >= 1 && item <= 12);
  const licenseText = formValue(form, 'licenses');
  const contractsText = formValue(form, 'long_contracts');
  const city = formValue(form, 'city');
  const street = formValue(form, 'street');
  const house = formValue(form, 'house');
  const notes = formValue(form, 'address_notes');
  const address = [city, street, house, notes].filter(Boolean).join(', ');

  Object.assign(details, {
    business_type: choice('business_type'),
    property_type: ({ psn: 'free_purpose', production: 'production', kiosk: 'kiosk' })[type] || type || undefined,
    property_condition: choice('condition'),
    transfer_method: choice('transfer_method'),
    deal_composition: choice('deal_composition'),
    business_name: formValue(form, 'title') || undefined,
    short_description: formValue(form, 'short_description') || undefined,
    full_description: formValue(form, 'full_description') || undefined,
    sale_price: formNumber(form, 'price'),
    stock_included: formBoolean(form, 'stock_included'),
    stock_value: formNumber(form, 'stock_price'),
    country: formValue(form, 'country') || undefined,
    city: city || undefined,
    street: street || undefined,
    house: house || undefined,
    query: address || undefined,
    area_sqm: formNumber(form, 'area'),
    floor_number: formNumber(form, 'floor'),
    has_separate_entrance: formBoolean(form, 'separate_entrance'),
    parking_spaces: formNumber(form, 'parking'),
    ceiling_height: formNumber(form, 'ceiling_height'),
    equipment_list: equipment,
    staff_count: formNumber(form, 'staff_total'),
    staff_details: staff,
    working_hours: hours || undefined,
    business_age_months: formNumber(form, 'business_age'),
    has_licenses: licenseText ? true : undefined,
    has_contracts: contractsText ? true : undefined,
    sale_reason: formValue(form, 'sale_reason') || undefined,
    stay_as_consultant_months: formNumber(form, 'support_months'),
    video_url: formValue(form, 'video_url') || undefined,
    monthly_financials: financials,
    average_check: formNumber(form, 'avg_check'),
    monthly_orders: formNumber(form, 'orders_per_month'),
    monthly_clients_unique: formNumber(form, 'unique_clients'),
    cost_structure: formValue(form, 'cost_items').split(/[\n,;]+/).map((item) => item.trim()).filter(Boolean),
    seasonality_months: splitNumbers(formValue(form, 'peak_months')),
    peak_hours: formValue(form, 'peak_hours') ? [formValue(form, 'peak_hours')] : [],
    supplier_contracts: formBoolean(form, 'good_contracts'),
    supplier_details: formValue(form, 'supplier_terms') || undefined,
    debts_receivable: formNumber(form, 'receivables'),
    debts_payable: formNumber(form, 'payables'),
    legal_claims: formBoolean(form, 'lawsuits'),
    legal_claims_details: formValue(form, 'lawsuits_description') || undefined,
    equipment_lease: formBoolean(form, 'leased_equipment'),
    monthly_loan_payments: formNumber(form, 'monthly_payments'),
    customer_base_size: formNumber(form, 'client_base'),
    repeat_customer_rate: formNumber(form, 'regular_share') === undefined ? undefined : formNumber(form, 'regular_share') / 100,
    seller_status: formValue(form, 'seller_status') || undefined,
    seller_name: formValue(form, 'seller_name') || undefined,
    seller_phone: formValue(form, 'seller_phone') || undefined,
    seller_email: formValue(form, 'seller_email') || undefined,
    seller_inn: formValue(form, 'seller_inn') || undefined,
    seller_ogrnip: formValue(form, 'seller_ogrnip') || undefined,
  });
  return details;
}

const uploadFields = {
  fire_plan: 'evacuation_plan_doc',
  fire_declaration: 'fire_declaration_doc',
  fire_contract: 'fire_service_contract_doc',
  sanitary_conclusion: 'san_epid_conclusion',
  floor_plan: 'floor_plan_image',
  doc_npd: 'income_statement_doc',
  doc_tax: 'tax_certificate_doc',
  doc_lease: 'lease_agreement_doc',
  doc_property: 'ownership_doc',
  doc_passport: 'passport_copy_doc',
  photo_main: 'main_photo',
  photos_extra: 'photos',
};

async function uploadSelectedFiles(form, listingId) {
  for (const [inputName, apiField] of Object.entries(uploadFields)) {
    const input = formControls(form).find((element) => element.name === inputName);
    if (!input?.files?.length) continue;
    for (const file of input.files) await uploadListingFile(listingId, apiField, file);
  }
}

function bindRepeaters(form) {
  for (const kind of ['equipment', 'staff', 'month']) {
    const button = $(`[data-add="${kind}"]`, form);
    const roots = () => $$(`[data-repeat="${kind}"]`, form);
    roots().forEach((root, index) => {
      const prefix = kind === 'month' ? 'month_' : kind === 'equipment' ? 'equipment_condition_' : null;
      if (prefix) $$(`input[name^="${prefix}"]`, root).forEach((input) => { input.name = `${prefix}${index + 1}`; });
    });
    button?.addEventListener('click', () => {
      const current = roots();
      const copy = current.at(-1)?.cloneNode(true);
      if (!copy) return;
      const index = current.length + 1;
      copy.querySelectorAll('input, textarea, select').forEach((field) => {
        if (field.type === 'radio' || field.type === 'checkbox') field.checked = false;
        else if (field.type !== 'file') field.value = '';
        if (kind === 'month' && field.name.startsWith('month_')) field.name = `month_${index}`;
        if (kind === 'equipment' && field.name.startsWith('equipment_condition_')) field.name = `equipment_condition_${index}`;
      });
      copy.querySelectorAll('.dropdown__value').forEach((value) => { value.textContent = 'Выберите из списка'; });
      current.at(-1).after(copy);
    });
  }
}

function fillRepeatedField(root, name, value, radioValue) {
  const fields = formControls(root).filter((field) => field.name === name);
  if (!fields.length || value === undefined || value === null) return;
  if (fields[0].type === 'radio' || fields[0].type === 'checkbox') {
    const expected = radioValue ?? String(value);
    const selected = fields.find((field) => String(field.value) === expected);
    if (selected) selected.checked = true;
    return;
  }
  if (fields[0].type !== 'file') fields[0].value = Array.isArray(value) ? value.join(', ') : String(value);
}

function hydrateListingDraft(form, item) {
  const names = {
    business_name: 'title', short_description: 'short_description', full_description: 'full_description',
    sale_price: 'price', stock_value: 'stock_price', country: 'country', city: 'city', street: 'street', house: 'house',
    area_sqm: 'area', floor_number: 'floor', ceiling_height: 'ceiling_height', parking_spaces: 'parking',
    business_age_months: 'business_age', sale_reason: 'sale_reason', stay_as_consultant_months: 'support_months',
    seller_name: 'seller_name', seller_phone: 'seller_phone', seller_email: 'seller_email', seller_inn: 'seller_inn', seller_ogrnip: 'seller_ogrnip',
    video_url: 'video_url', average_check: 'avg_check', monthly_orders: 'orders_per_month',
    monthly_clients_unique: 'unique_clients', supplier_details: 'supplier_terms', debts_receivable: 'receivables',
    debts_payable: 'payables', legal_claims_details: 'lawsuits_description', monthly_loan_payments: 'monthly_payments',
    customer_base_size: 'client_base',
  };
  Object.entries(names).forEach(([key, name]) => fillRepeatedField(form, name, item[key]));
  const boolFields = {
    stock_included: 'stock_included', has_separate_entrance: 'separate_entrance', supplier_contracts: 'good_contracts',
    legal_claims: 'lawsuits', equipment_lease: 'leased_equipment',
  };
  Object.entries(boolFields).forEach(([key, name]) => {
    if (item[key] !== null && item[key] !== undefined) fillRepeatedField(form, name, item[key], item[key] ? 'yes' : 'no');
  });
  const choiceValues = {
    business_type: item.business_type,
    transfer_method: item.transfer_method,
    deal_composition: item.deal_composition,
    seller_status: item.seller_status,
    condition: item.property_condition,
    property_type: ({ free_purpose: 'psn', production: 'production', kiosk: 'kiosk' })[item.property_type] || item.property_type,
  };
  Object.entries(choiceValues).forEach(([name, value]) => {
    const field = formControls(form).find((control) => control.name === name && String(control.value) === String(value));
    if (field && (field.type === 'radio' || field.type === 'checkbox')) field.checked = true;
    else if (field) field.value = value;
  });
  fillRepeatedField(form, 'regular_share', item.repeat_customer_rate === null || item.repeat_customer_rate === undefined ? undefined : Math.round(item.repeat_customer_rate * 100));
  fillRepeatedField(form, 'cost_items', item.cost_structure);
  fillRepeatedField(form, 'peak_months', item.seasonality_months);
  fillRepeatedField(form, 'peak_hours', item.peak_hours);

  const equipment = item.equipment_list || [];
  while ($$('[data-repeat="equipment"]', form).length < equipment.length) $('[data-add="equipment"]', form)?.click();
  $$('[data-repeat="equipment"]', form).forEach((root, index) => {
    const entry = equipment[index];
    if (!entry) return;
    fillRepeatedField(root, 'equipment_name[]', entry.equipment_name);
    fillRepeatedField(root, 'equipment_brand[]', entry.equipment_brand);
    fillRepeatedField(root, 'equipment_year[]', entry.equipment_purchase_year);
    fillRepeatedField(root, 'equipment_price[]', entry.equipment_value);
    const condition = ({ 'отличное': 'excellent', 'хорошее': 'good', 'требует замены/ремонта': 'repair' })[entry.equipment_condition] || entry.equipment_condition;
    fillRepeatedField(root, `equipment_condition_${index + 1}`, condition);
  });
  const staff = item.staff_details || [];
  while ($$('[data-repeat="staff"]', form).length < staff.length) $('[data-add="staff"]', form)?.click();
  $$('[data-repeat="staff"]', form).forEach((root, index) => {
    const entry = staff[index];
    if (!entry) return;
    fillRepeatedField(root, 'staff_position[]', entry.position);
    fillRepeatedField(root, 'staff_count[]', entry.count);
    fillRepeatedField(root, 'staff_salary[]', entry.salary);
  });
  const financeNames = {
    revenue: 'revenue[]', total_expenses: 'costs_total[]', utilities_expenses: 'costs_utilities[]',
    rent_expenses: 'costs_rent[]', payroll_expenses: 'costs_payroll[]', purchases_expenses: 'costs_purchases[]',
    taxes_expenses: 'costs_taxes[]', marketing_expenses: 'costs_marketing[]', other_expenses: 'costs_other[]', net_profit: 'net_profit[]',
  };
  const finances = item.monthly_financials || [];
  while ($$('[data-repeat="month"]', form).length < finances.length) $('[data-add="month"]', form)?.click();
  $$('[data-repeat="month"]', form).forEach((root, index) => {
    const entry = finances[index];
    if (!entry) return;
    fillRepeatedField(root, `month_${index + 1}`, Number(String(entry.month).slice(-2)));
    Object.entries(financeNames).forEach(([key, name]) => fillRepeatedField(root, name, entry[key]));
  });
}

function bindCreateListing() {
  const form = $('.wizard__form');
  if (!form) return;
  bindRepeaters(form);
  let saving = false;
  const existingId = listingIdFromHash();
  if (existingId) {
    getListing(existingId).then((item) => {
      hydrateListingDraft(form, item);
      notify('Черновик загружен. Измените данные и отправьте объявление.');
    }).catch((error) => notify(error.message, 'error'));
  }
  form.addEventListener('click', async (event) => {
    const finish = event.target.closest('a.next[href="#success"]');
    if (!finish || saving) return;
    event.preventDefault();
    if (!formValue(form, 'seller_status')) return notify('Выберите статус продавца.', 'error');
    const payload = draftFromForm(form);
    if (!payload.business_type || !payload.property_type || !payload.transfer_method || !payload.deal_composition) {
      return notify('Заполните категорию, тип помещения, состав сделки и способ передачи.', 'error');
    }
    saving = true;
    finish.setAttribute('aria-disabled', 'true');
    try {
      const listing = existingId ? await updateListing(existingId, payload) : await createListing(payload);
      const id = listing.id || existingId;
      await uploadSelectedFiles(form, id);
      await submitListing(id);
      location.hash = 'success';
      notify('Объявление отправлено на проверку.');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      saving = false;
      finish.removeAttribute('aria-disabled');
    }
  });
  form.addEventListener('input', (event) => {
    const field = event.target;
    if (!field.matches('.js-time')) return;
    let digits = field.value.replace(/\D/g, '').slice(0, 4);
    if (digits.length === 1 && Number(digits) > 2) digits = `0${digits}`;
    if (digits.length >= 2 && Number(digits.slice(0, 2)) > 23) digits = `23${digits.slice(2)}`;
    if (digits.length >= 3 && Number(digits[2]) > 5) digits = `${digits.slice(0, 2)}5${digits.slice(3)}`;
    field.value = digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits;
  });
}

function setKvValue(root, label, value) {
  if (value === undefined || value === null || value === '') return;
  const row = $$('.kv__row', root).find((element) => $('dt', element)?.textContent.trim() === label);
  if (row) $('dd', row).textContent = String(value);
}

function displayEnum(value) {
  const labels = {
    food: 'Общественное питание', retail: 'Розничная торговля', services: 'Услуги', beauty: 'Красота и здоровье',
    entertainment: 'Развлечения', education: 'Образование', logistics: 'Логистика', auto: 'Автобизнес',
    hospitality: 'Гостиничный бизнес', manufacturing: 'Производство', itd: 'IT и цифровые сервисы',
    vending: 'Вендинг', other: 'Другое', free_purpose: 'Помещение свободного назначения', production: 'Производственное',
    kiosk: 'Киоск', needs_repair: 'Требует ремонта', cosmetic_repair: 'Косметический ремонт',
    good_condition: 'Хорошее', excellent_condition: 'Отличное', owner: 'В собственности',
    owner_with_rent: 'Аренда', with_stock: 'С товарным остатком', with_contracts: 'С контрактами',
    full_transfer_training: 'Полная передача с обучением', transfer_no_training: 'Передача без обучения',
    assets_only: 'Передача активов', ip: 'Индивидуальный предприниматель', self_employed: 'Самозанятый',
  };
  return labels[value] || value || '';
}

function makeDetailSection(title, entries) {
  const rows = entries.filter(([, value]) => value !== undefined && value !== null && value !== '');
  if (!rows.length) return null;
  const section = document.createElement('section');
  section.className = 'box';
  const heading = document.createElement('h2');
  heading.className = 'heading heading--box';
  heading.textContent = title;
  const list = document.createElement('dl');
  list.className = 'kv';
  rows.forEach(([label, value]) => {
    const row = document.createElement('div');
    row.className = 'kv__row';
    const term = document.createElement('dt');
    term.textContent = label;
    const description = document.createElement('dd');
    description.textContent = String(value);
    row.append(term, description);
    list.append(row);
  });
  section.append(heading, list);
  return section;
}

function renderDetailTab(id, content) {
  const body = $(`#${id} .tab__body`);
  if (!body) return;
  body.replaceChildren(...content.filter(Boolean));
  if (!body.childElementCount) body.append(emptyState('Продавец пока не добавил эти сведения.'));
}

function buildListingMapSection(item) {
  const section = document.createElement('section');
  section.className = 'listing-map';
  const title = document.createElement('h2');
  title.className = 'listing-map__title';
  title.textContent = 'Местоположение на карте';
  const canvas = document.createElement('div');
  canvas.className = 'listing-map__canvas';
  canvas.setAttribute('role', 'application');
  canvas.setAttribute('aria-label', 'Расположение объявления на карте');
  const note = document.createElement('p');
  note.className = 'listing-map__note';
  const coordinates = item.location_point?.coordinates;
  const longitude = Array.isArray(coordinates) ? Number(coordinates[0]) : NaN;
  const latitude = Array.isArray(coordinates) ? Number(coordinates[1]) : NaN;
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    canvas.hidden = true;
    note.textContent = 'Для этого объявления координаты пока не определены.';
  } else if (!window.L) {
    canvas.hidden = true;
    note.textContent = 'Не удалось загрузить библиотеку карты.';
  } else {
    const initialize = () => requestAnimationFrame(() => {
      if (!canvas.isConnected) return;
      const zoom = item.coordinate_precision === 'city' ? 12 : 15;
      const map = window.L.map(canvas, { scrollWheelZoom: false }).setView([latitude, longitude], zoom);
      addOpenStreetMapTiles(map);
      window.L.circleMarker([latitude, longitude], {
        radius: 10,
        color: '#ffffff',
        weight: 3,
        fillColor: '#680A18',
        fillOpacity: 1,
        className: 'miero-map-marker miero-map-marker--selected',
      }).addTo(map);
      requestAnimationFrame(() => map.invalidateSize());
    });
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        initialize();
      });
      observer.observe(canvas);
    } else {
      initialize();
    }
    if (item.coordinate_precision === 'city') {
      note.textContent = 'Точка приблизительная: указана только привязка к городу.';
    }
  }
  section.append(title, canvas, note);
  return section;
}

function renderListingDetails(item) {
  const yesNo = (value) => value === null || value === undefined ? '' : value ? 'Да' : 'Нет';
  const moneyOrEmpty = (value) => value === null || value === undefined ? '' : formatMoney(value);
  const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
  const financials = Array.isArray(item.monthly_financials) ? item.monthly_financials : [];
  const average = (key) => financials.length
    ? financials.reduce((sum, row) => sum + Number(row[key] || 0), 0) / financials.length
    : undefined;
  const revenue = item.avg_monthly_revenue ?? average('revenue');
  const profit = average('net_profit');
  const payback = Number(item.sale_price) > 0 && Number(profit) > 0 ? Number(item.sale_price) / Number(profit) / 12 : undefined;

  const description = document.createElement('div');
  const descriptionTitle = document.createElement('h2');
  descriptionTitle.className = 'heading heading--xl';
  descriptionTitle.textContent = 'Описание';
  const descriptionText = document.createElement('p');
  descriptionText.className = 'text';
  descriptionText.textContent = item.full_description || item.short_description || 'Описание пока не добавлено.';
  description.append(descriptionTitle, descriptionText, buildListingMapSection(item));
  const reason = item.sale_reason ? makeDetailSection('Причина продажи', [['Причина', item.sale_reason]]) : null;
  renderDetailTab('tab-main', [description, reason, makeDetailSection('Основные характеристики', [
    ['Тип бизнеса', displayEnum(item.business_type)], ['Состав сделки', displayEnum(item.deal_composition)],
    ['Тип коммерческой недвижимости', displayEnum(item.property_type)], ['Состояние помещения', displayEnum(item.property_condition)],
    ['Способ передачи бизнеса', displayEnum(item.transfer_method)], ['Товарный остаток включён в цену', yesNo(item.stock_included)],
    ['Стоимость товарного остатка', moneyOrEmpty(item.stock_value)],
  ])]);

  const location = item.location || {};
  renderDetailTab('tab-location', [makeDetailSection('Расположение и помещение', [
    ['Страна', location.country || item.country], ['Город', location.city || item.city], ['Улица', location.street || item.street],
    ['Дом', location.house || item.house], ['Этаж', item.floor_number], ['Площадь помещения', item.area_sqm ? `${item.area_sqm} м²` : ''],
    ['Отдельный вход', yesNo(item.has_separate_entrance)], ['Количество парковочных мест', item.parking_spaces],
    ['Высота потолков', item.ceiling_height ? `${item.ceiling_height} м` : ''], ['Режим работы', item.working_hours],
  ])]);

  const equipment = Array.isArray(item.equipment_list) ? item.equipment_list : [];
  renderDetailTab('tab-equipment', equipment.map((entry) => makeDetailSection(entry.equipment_name || 'Оборудование', [
    ['Бренд/модель', entry.equipment_brand], ['Состояние', displayEnum(entry.equipment_condition)],
    ['Год приобретения', entry.equipment_purchase_year], ['Стоимость', moneyOrEmpty(entry.equipment_value)],
  ])));

  const months = financials.map((entry) => makeDetailSection(monthNames[Number(String(entry.month).slice(-2)) - 1] || entry.month, [
    ['Выручка', moneyOrEmpty(entry.revenue)], ['Общие расходы', moneyOrEmpty(entry.total_expenses)],
    ['ЖКХ', moneyOrEmpty(entry.utilities_expenses)], ['Аренда', moneyOrEmpty(entry.rent_expenses)],
    ['Фонд оплаты труда', moneyOrEmpty(entry.payroll_expenses)], ['Закупки', moneyOrEmpty(entry.purchases_expenses)],
    ['Налоги', moneyOrEmpty(entry.taxes_expenses)], ['Маркетинг', moneyOrEmpty(entry.marketing_expenses)],
    ['Прочие расходы', moneyOrEmpty(entry.other_expenses)], ['Чистая прибыль', moneyOrEmpty(entry.net_profit)],
  ]));
  renderDetailTab('tab-finance', [makeDetailSection('Показатели', [
    ['Средняя выручка в месяц', moneyOrEmpty(revenue)], ['Средняя прибыль в месяц', moneyOrEmpty(profit)],
    ['Средний чек', moneyOrEmpty(item.average_check)], ['Заказов в месяц', item.monthly_orders],
    ['Уникальных клиентов в месяц', item.monthly_clients_unique],
    ['Месяцы повышенной загрузки', item.seasonality_months?.map((month) => monthNames[month - 1]).filter(Boolean).join(', ')],
    ['Часы пиковой нагрузки', item.peak_hours?.join(', ')], ['Контракты с поставщиками', yesNo(item.supplier_contracts)],
    ['Условия поставщиков', item.supplier_details], ['Дебиторская задолженность', moneyOrEmpty(item.debts_receivable)],
    ['Кредиторская задолженность', moneyOrEmpty(item.debts_payable)], ['Судебные претензии', yesNo(item.legal_claims)],
    ['Пояснение по претензиям', item.legal_claims_details], ['Оборудование в лизинге', yesNo(item.equipment_lease)],
    ['Ежемесячные платежи по кредитам и лизингу', moneyOrEmpty(item.monthly_loan_payments)],
    ['Размер клиентской базы', item.customer_base_size],
    ['Доля постоянных клиентов', item.repeat_customer_rate === null || item.repeat_customer_rate === undefined ? '' : `${Math.round(item.repeat_customer_rate * 100)}%`],
    ['Структура затрат', item.cost_structure?.join(', ')],
  ]), ...months]);

  const staff = Array.isArray(item.staff_details) ? item.staff_details : [];
  const staffTable = staff.length ? document.createElement('table') : null;
  if (staffTable) {
    staffTable.className = 'staff-table';
    const tbody = document.createElement('tbody');
    const header = document.createElement('tr');
    ['Должность', 'Количество', 'Средняя зарплата'].forEach((text) => {
      const cell = document.createElement('th'); cell.textContent = text; header.append(cell);
    });
    const thead = document.createElement('thead'); thead.append(header);
    staff.forEach((entry) => {
      const row = document.createElement('tr');
      [entry.position, `${entry.count} чел.`, formatMoney(entry.salary)].forEach((text) => {
        const cell = document.createElement('td'); cell.textContent = text; row.append(cell);
      });
      tbody.append(row);
    });
    staffTable.append(thead, tbody);
  }
  const staffTitle = document.createElement('h2');
  staffTitle.className = 'heading';
  staffTitle.textContent = 'Список сотрудников';
  renderDetailTab('tab-staff', [makeDetailSection('Персонал и бизнес', [
    ['Количество сотрудников', item.staff_count], ['Возраст бизнеса', item.business_age_months === null || item.business_age_months === undefined ? '' : `${item.business_age_months} мес.`],
    ['Наличие лицензий', yesNo(item.has_licenses)], ['Долгосрочные контракты', yesNo(item.has_contracts)],
  ]), staffTable ? staffTitle : null, staffTable]);

  // Compliance documents are private and are intentionally not part of the public catalog response.
  $('#tab-fire')?.remove();
  $$('a[href="#tab-fire"]').forEach((link) => link.remove());
  $$('.pager__btn--next[href="#tab-fire"]').forEach((link) => link.remove());

  const metrics = [...$$('.stats__item')];
  const metricValues = [revenue, profit, payback];
  metrics.forEach((row, index) => {
    const value = metricValues[index];
    if (value === undefined || value === null || !Number.isFinite(Number(value))) row.hidden = true;
    else $('dd', row).textContent = index === 2 ? `${Number(value).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} лет` : formatMoney(value);
  });
}

async function loadListingDetail() {
  const titleNode = $('.summary__title');
  if (titleNode) titleNode.textContent = 'Загрузка объявления…';
  const addressNode = $('.summary__address');
  if (addressNode) addressNode.textContent = '';
  const priceNode = $('.summary__price');
  if (priceNode) priceNode.textContent = '';
  $('.seller__name')?.replaceChildren();
  $('.seller__role')?.replaceChildren();
  $('.seller__seen')?.remove();
  $$('.seller__btn').forEach((button) => { button.hidden = true; });
  $('.summary__fav')?.setAttribute('hidden', '');
  $('.summary__badge')?.replaceChildren();
  $('#tab-fire')?.remove();
  $$('a[href="#tab-fire"]').forEach((link) => link.remove());
  renderDetailTab('tab-main', [emptyState('Загрузка объявления…')]);
  renderDetailTab('tab-location', [emptyState('Загрузка объявления…')]);
  renderDetailTab('tab-equipment', [emptyState('Загрузка объявления…')]);
  renderDetailTab('tab-finance', [emptyState('Загрузка объявления…')]);
  renderDetailTab('tab-staff', [emptyState('Загрузка объявления…')]);
  $$('.stats__item').forEach((row) => { row.hidden = true; });
  const id = listingIdFromHash();
  if (!id) return notify('Откройте объявление из каталога, чтобы посмотреть его карточку.', 'error');
  try {
    const item = await getPublishedListing(id);
    const title = item.business_name || 'Бизнес на продаже';
    const city = item.location?.city || item.city || '';
    const address = [city, item.location?.street || item.street, item.location?.house || item.house].filter(Boolean).join(', ');
    $('.summary__title')?.replaceChildren(document.createTextNode(title));
    $('.summary__address')?.replaceChildren(document.createTextNode(address || 'Местоположение не указано'));
    $('.summary__price')?.replaceChildren(document.createTextNode(formatMoney(item.sale_price)));
    const badge = $('.summary__badge');
    if (badge) badge.textContent = item.verification_status === 'deep' ? 'Глубокая проверка' : 'Базовая проверка';
    const mainPhoto = $('.gallery__main');
    const photos = [item.main_photo, ...(item.photos || [])].filter(Boolean);
    placeImage(mainPhoto, photos[0]);
    $('.gallery__thumb--more')?.setAttribute('hidden', '');
    $$('.gallery__thumb', document).forEach((button, index) => {
      const image = photos[index + 1];
      if (image) placeImage(button, image);
      else button.hidden = true;
      button.addEventListener('click', () => placeImage(mainPhoto, image));
    });
    renderListingDetails(item);
    const sellerName = $('.seller__name');
    if (sellerName && item.seller_name) sellerName.textContent = item.seller_name;
    const sellerRole = $('.seller__role');
    if (sellerRole) sellerRole.textContent = displayEnum(item.seller_status) || 'Продавец';
    $('.seller__seen')?.remove();
    const contact = $('.seller__btn--primary');
    if (contact && item.seller_id) {
      contact.hidden = false;
      contact.addEventListener('click', async (event) => {
        event.preventDefault();
        if (!getAccessToken()) {
          sessionStorage.setItem('mieroventure.redirect', location.href);
          location.href = 'login.html';
          return;
        }
        try {
          const conversation = await createConversation(item.seller_id);
          location.href = `messages.html#${encodeURIComponent(conversation.id || conversation._id)}`;
        } catch (error) {
          notify(error.message, 'error');
        }
      });
    } else if (contact) {
      contact.hidden = true;
    }
    const phoneLink = $('.seller__btn--outline');
    if (!item.seller_phone && phoneLink) phoneLink.hidden = true;
    else if (phoneLink) { phoneLink.href = `tel:${item.seller_phone}`; phoneLink.hidden = false; }
    const favorite = $('.summary__fav');
    if (favorite) {
      favorite.hidden = false;
      favorite.dataset.listingId = id;
      updateIconFavorite(favorite, favoriteIds().includes(String(id)));
    }
    if (getAccessToken()) {
      me().then((viewer) => {
        loadedUser = viewer;
        if (viewer.role !== 'moderator' || $('.moderator-remove-listing')) return;
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'moderator-remove-listing';
        removeButton.textContent = 'Снять объявление с каталога';
        removeButton.addEventListener('click', async () => {
          const reason = prompt('Укажите причину снятия объявления:');
          if (!reason || reason.trim().length < 3) return;
          removeButton.disabled = true;
          try {
            await removeFromCatalog(id, reason.trim());
            notify('Команда на снятие с каталога отправлена.');
            location.href = 'catalog.html';
          } catch (error) {
            notify(error.message, 'error');
            removeButton.disabled = false;
          }
        });
        $('.summary__info')?.append(removeButton);
      }).catch(() => {});
    }
  } catch (error) {
    notify(error.message, 'error');
  }
}

async function loadModerationQueue() {
  const list = $('.queue__list');
  if (!list) return [];
  const template = $('li', list);
  list.replaceChildren();
  const loading = document.createElement('li');
  loading.append(emptyState('Загрузка очереди…'));
  list.append(loading);
  try {
    const result = await getModerationCases();
    const items = asItems(result);
    list.replaceChildren();
    if (!items.length) {
      const li = document.createElement('li');
      li.append(emptyState('Очередь на модерацию пуста.'));
      list.append(li);
      return [];
    }
    items.forEach((item) => {
      const row = template?.cloneNode(true) || document.createElement('li');
      const card = $('.mod-card', row) || row;
      const listing = item.listing_snapshot || {};
      const ai = item.analytics_reports?.ai_report || {};
      const flags = Array.isArray(ai.red_flags) ? ai.red_flags : [];
      card.dataset.listingId = item.listing_id;
      card.dataset.price = String(Number(listing.sale_price) || 0);
      card.dataset.order = String(Date.parse(item.created_at || '') || 0);
      card.dataset.score = String(Number(ai.red_flag_score) || 0);
      card.dataset.risk = String(({ low: 1, moderate: 2, high: 3, critical: 4 })[ai.red_flag_rating] || 0);
      $('.mod-card__title', card)?.replaceChildren(document.createTextNode(listing.business_name || 'Без названия'));
      $('.mod-card__price', card)?.replaceChildren(document.createTextNode(formatMoney(listing.sale_price)));
      const meta = $$('.mod-card__meta li', card);
      setIconText(meta[0], listing.city || 'Город не указан');
      setIconText(meta[1], displayEnum(listing.business_type) || 'Другое');
      const date = $('.mod-card__date time', card);
      if (date && item.created_at) {
        date.dateTime = item.created_at;
        date.textContent = new Date(item.created_at).toLocaleDateString('ru-RU');
      }
      $('.score', card)?.setAttribute('hidden', '');
      const issueSection = $('.mod-card__issues', card);
      const issueList = $('.issues__list', card);
      if (issueList) {
        issueList.replaceChildren();
        flags.slice(0, 3).forEach((flag) => {
          const issue = document.createElement('li');
          issue.className = 'issue';
          const code = document.createElement('span');
          code.className = 'issue__code';
          code.textContent = flag.code || 'AI';
          const description = document.createElement('span');
          description.className = 'issue__text';
          description.textContent = flag.evidence || flag.code || 'Требуется ручная проверка';
          issue.append(code, description);
          issueList.append(issue);
        });
      }
      issueSection?.toggleAttribute('hidden', flags.length === 0);
      const risk = $('.risk', card);
      const riskLabel = ({ critical: 'Критический риск', high: 'Высокий риск', moderate: 'Требуется проверка', low: 'Низкий риск' })[ai.red_flag_rating];
      if (risk && riskLabel && ai.red_flag_rating !== 'low') {
        risk.className = `risk risk--${ai.red_flag_rating}`;
        const label = risk.querySelector('span:last-child');
        if (label) label.textContent = riskLabel;
        risk.hidden = false;
      } else if (risk) risk.hidden = true;
      const link = $('.mod-card__more', card);
      if (link) link.href = `moderation-detail.html#${encodeURIComponent(item.id)}`;
      list.append(row);
    });
    return items;
  } catch (error) {
    list.replaceChildren();
    const li = document.createElement('li');
    li.append(emptyState(`Не удалось загрузить очередь: ${error.message}`));
    list.append(li);
    return [];
  }
}

async function bindModerationDetail() {
  const container = $('.detail__container');
  const objectTemplate = $('.object-card', container)?.cloneNode(true);
  const decisionTemplate = $('.decision-row', container)?.cloneNode(true);
  container?.replaceChildren(emptyState('Загрузка объявления…'));
  const id = listingIdFromHash();
  if (!id) {
    container?.replaceChildren(emptyState('Откройте объявление из очереди модерации.'));
    return;
  }
  try {
    const moderationCase = await getModerationCase(id);
    const viewableStatuses = new Set(['pending', 'approved', 'auto_approved', 'removed']);
    if (!moderationCase || !viewableStatuses.has(moderationCase.status)) {
      container?.replaceChildren(emptyState('Объявление не найдено в очереди модерации.', 'Вернуться в очередь', 'moderation-queue.html'));
      return;
    }
    const item = moderationCase.listing_snapshot || {};
    const aiReport = moderationCase.analytics_reports?.ai_report || {};
    const scriptsReport = moderationCase.analytics_reports?.scripts_report || {};
    if (!objectTemplate || !decisionTemplate || !container) return;
    container.replaceChildren(objectTemplate, decisionTemplate);
    const title = $('.object-title', container);
    if (title) title.textContent = item.business_name || 'Объявление';
    const address = [item.city, item.street, item.house].filter(Boolean).join(', ');
    const addressNode = $('.object-address', container);
    if (addressNode) addressNode.textContent = address || 'Местоположение не указано';
    $('.object-price', container)?.replaceChildren(document.createTextNode(formatMoney(item.sale_price)));
    const finances = item.monthly_financials || [];
    const average = (key) => finances.length
      ? finances.reduce((sum, row) => sum + Number(row[key] || 0), 0) / finances.length
      : undefined;
    const revenue = average('revenue');
    const expenses = average('total_expenses');
    const profit = average('net_profit');
    const payback = Number(item.sale_price) > 0 && Number(profit) > 0 ? Number(item.sale_price) / Number(profit) / 12 : undefined;
    const values = [revenue, profit, payback];
    $$('.object-stats > div', container).forEach((row, index) => {
      const value = values[index];
      row.hidden = value === undefined;
      if (value !== undefined) $('strong', row).textContent = index === 2 ? `${value.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} лет` : formatMoney(value);
    });
    const metrics = [revenue, expenses, profit, revenue && expenses !== undefined ? `${((revenue - expenses) / revenue * 100).toFixed(1)}%` : undefined, payback];
    $$('.object-metrics > div', container).forEach((row, index) => {
      row.hidden = metrics[index] === undefined;
      if (metrics[index] !== undefined) $('strong', row).textContent = index === 3
        ? metrics[index]
        : index === 4 ? `${metrics[index].toLocaleString('ru-RU', { maximumFractionDigits: 1 })} лет` : `${formatMoney(metrics[index])} / месяц`;
    });
    const photos = [item.files?.main_photo, ...(item.files?.photos || [])].filter(Boolean);
    const mainPhoto = $('.object-gallery__main', container);
    placeImage(mainPhoto, photos[0]);
    $$('.gallery-thumb', container).forEach((thumb, index) => {
      const url = photos[index + 1];
      thumb.hidden = !url;
      if (url) placeImage(thumb, url);
    });
    const details = document.createElement('section');
    details.className = 'analysis-grid';
    const decisionRow = $('.decision-row', container);
    const isPending = moderationCase.status === 'pending';
    const isPublished = ['approved', 'auto_approved'].includes(moderationCase.status);
    if (decisionRow) decisionRow.hidden = !isPending;
    const description = document.createElement('div');
    description.className = 'analysis-block';
    const descriptionTitle = document.createElement('h2');
    descriptionTitle.className = 'section-title';
    descriptionTitle.textContent = 'Описание и сведения';
    const descriptionText = document.createElement('p');
    descriptionText.textContent = item.full_description || item.short_description || 'Продавец не добавил описание.';
    description.append(descriptionTitle, descriptionText);
    details.append(description);
    const listingFacts = makeDetailSection('Данные объявления', [
      ['Тип бизнеса', displayEnum(item.business_type)], ['Тип помещения', displayEnum(item.property_type)],
      ['Состояние помещения', displayEnum(item.property_condition)], ['Состав сделки', displayEnum(item.deal_composition)],
      ['Способ передачи', displayEnum(item.transfer_method)], ['Продавец', item.seller_name], ['Статус продавца', displayEnum(item.seller_status)],
      ['ИНН', item.seller_inn], ['ОГРНИП', item.seller_ogrnip], ['Причина продажи', item.sale_reason],
      ['Проверка', moderationCase.verification_level === 'deep' ? 'Углублённая' : 'Базовая'],
    ]);
    if (listingFacts) details.append(listingFacts);
    const financialDetails = finances.map((row) => makeDetailSection(row.month, [
      ['Выручка', row.revenue === undefined ? '' : formatMoney(row.revenue)],
      ['Расходы', row.total_expenses === undefined ? '' : formatMoney(row.total_expenses)],
      ['Чистая прибыль', row.net_profit === undefined ? '' : formatMoney(row.net_profit)],
    ]));
    details.append(...financialDetails.filter(Boolean));
    const docLabels = {
      passport_copy_doc: 'Копия паспорта', tax_certificate_doc: 'Налоговая справка', income_statement_doc: 'Отчёт о доходах',
      lease_agreement_doc: 'Договор аренды', ownership_doc: 'Документ о собственности', evacuation_plan_doc: 'План эвакуации',
      fire_declaration_doc: 'Пожарная декларация', fire_service_contract_doc: 'Договор пожарного обслуживания',
      san_epid_conclusion: 'Санитарное заключение',
    };
    const documentFields = moderationCase.document_fields || [];
    if (documentFields.length) {
      const documents = document.createElement('section');
      documents.className = 'analysis-block';
      const heading = document.createElement('h2');
      heading.className = 'section-title';
      heading.textContent = 'Закрытые документы';
      const documentList = document.createElement('ul');
      documentFields.forEach((field) => {
        const entry = document.createElement('li');
        const link = document.createElement('a');
        link.href = '#';
        link.textContent = `Открыть: ${docLabels[field] || field}`;
        link.addEventListener('click', async (event) => {
          event.preventDefault();
          try { await openModerationDocument(moderationCase.id, field); }
          catch (error) { notify(error.message, 'error'); }
        });
        entry.append(link);
        documentList.append(entry);
      });
      documents.append(heading, documentList);
      details.append(documents);
    }
    const reportNotes = [
      ...(aiReport.moderation_reasons || []),
      ...((aiReport.red_flags || []).map((flag) => `${flag.code || 'Риск'}: ${flag.evidence || ''}`)),
      ...((scriptsReport.consistency_report || []).filter((check) => check.status !== 'ok').map((check) => `${check.check}: расхождение ${check.difference}`)),
    ].filter(Boolean);
    if (reportNotes.length) {
      const reports = makeDetailSection('Причины ручной проверки', reportNotes.map((text, index) => [`Пункт ${index + 1}`, text]));
      if (reports) details.append(reports);
    }
    const blockSeller = document.createElement('button');
    blockSeller.type = 'button';
    blockSeller.textContent = 'Добавить продавца в чёрный список';
    blockSeller.addEventListener('click', async () => {
      const reason = prompt('Укажите причину блокировки:');
      if (!reason || reason.trim().length < 3) return;
      try {
        await addToBlacklist(moderationCase.seller_id, reason.trim());
        notify('Продавец заблокирован, его объявления будут сняты с каталога.');
        location.href = 'blacklist.html';
      } catch (error) { notify(error.message, 'error'); }
    });
    details.append(blockSeller);
    if (isPublished) {
      const removeButton = document.createElement('button');
      removeButton.type = 'button';
      removeButton.className = 'moderator-remove-listing';
      removeButton.textContent = 'Снять объявление с каталога';
      removeButton.addEventListener('click', async () => {
        const reason = prompt('Укажите причину снятия объявления:');
        if (!reason || reason.trim().length < 3) return;
        removeButton.disabled = true;
        try {
          await removeFromCatalog(moderationCase.listing_id, reason.trim());
          notify('Команда на снятие с каталога отправлена.');
          location.href = 'moderation-queue.html';
        } catch (error) {
          notify(error.message, 'error');
          removeButton.disabled = false;
        }
      });
      details.append(removeButton);
    } else if (moderationCase.status === 'removed') {
      const removed = document.createElement('p');
      removed.textContent = `Объявление снято с каталога: ${moderationCase.decision_reason || 'причина не указана'}`;
      details.append(removed);
    }
    container.insertBefore(details, $('.decision-row', container));
    const buttons = isPending ? $$('.decision-row .decision') : [];
    buttons.forEach((button) => button.addEventListener('click', async () => {
      const approve = !button.classList.contains('decision--reject');
      const reason = approve ? null : prompt('Укажите безопасную для продавца причину отклонения:');
      if (!approve && (!reason || reason.trim().length < 3)) return;
      try {
        const verificationLevel = button.classList.contains('decision--outline') ? 'deep' : 'basic';
        await decideModerationCase(id, approve ? 'approve' : 'reject', reason?.trim(), verificationLevel);
        notify(approve ? 'Объявление одобрено.' : 'Объявление отклонено.');
        location.href = 'moderation-queue.html';
      } catch (error) {
        notify(error.message, 'error');
      }
    }));
  } catch (error) {
    container?.replaceChildren(emptyState(`Не удалось загрузить объявление: ${error.message}`, 'Вернуться в очередь', 'moderation-queue.html'));
    notify(error.message, 'error');
  }
}

function profileName(user) {
  return [user.first_name, user.patronymic, user.last_name].filter(Boolean).join(' ');
}

function showProfileDialog(user) {
  let dialog = $('.miero-dialog');
  if (!dialog) {
    dialog = document.createElement('dialog');
    dialog.className = 'miero-dialog';
    document.body.append(dialog);
  }
  dialog.innerHTML = `
    <form method="dialog" class="miero-profile-form">
      <h2>Редактировать профиль</h2>
      <label>Имя<input name="first_name" required maxlength="100"></label>
      <label>Фамилия<input name="last_name" required maxlength="100"></label>
      <label>Отчество<input name="patronymic" maxlength="100"></label>
      <label>Телефон<input name="phone" required minlength="5" maxlength="32"></label>
      <label>О себе<textarea name="business_description" maxlength="200" rows="3"></textarea></label>
      <div class="miero-dialog__actions"><button type="button" data-close>Отмена</button><button type="submit">Сохранить</button></div>
    </form>`;
  const form = $('form', dialog);
  for (const name of ['first_name', 'last_name', 'patronymic', 'phone', 'business_description']) {
    const field = form.elements.namedItem(name);
    if (field) field.value = user[name] || '';
  }
  $('[data-close]', dialog).addEventListener('click', () => dialog.close());
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = new FormData(form);
    try {
      loadedUser = await updateProfile(Object.fromEntries(values.entries()));
      applyProfile(loadedUser);
      dialog.close();
      notify('Профиль обновлён.');
    } catch (error) {
      notify(error.message, 'error');
    }
  }, { once: true });
  dialog.showModal();
}

function applyProfile(user) {
  $('main.profile')?.removeAttribute('aria-busy');
  const name = profileName(user) || user.email || 'Профиль';
  $$('.hero__name, .hero__user h1, .profile__name').forEach((element) => { element.textContent = name; });
  const contacts = $$('.hero__contacts a');
  const email = contacts.find((element) => element.href.startsWith('mailto:'));
  const phone = contacts.find((element) => element.href.startsWith('tel:'));
  if (email) { email.textContent = user.email; email.href = `mailto:${user.email}`; email.hidden = false; }
  if (phone && user.phone) { phone.textContent = user.phone; phone.href = `tel:${user.phone}`; phone.hidden = false; }
  const about = $('.about__text');
  if (about) about.textContent = user.business_description || 'Описание пока не добавлено.';
  $$('[role="switch"][name]').forEach((input) => {
    if (Object.hasOwn(user.notification_preferences || {}, input.name)) {
      input.checked = Boolean(user.notification_preferences[input.name]);
    }
  });
  $$('.settings').forEach((section) => { section.hidden = false; });
  $$('[role="switch"][name]').forEach((input) => { input.disabled = false; });
}

async function loadProfile() {
  const profileRoot = $('main.profile');
  $$('.hero__name, .hero__user h1, .profile__name').forEach((element) => { element.textContent = 'Загрузка профиля…'; });
  $$('.hero__contacts a').forEach((element) => { element.hidden = true; });
  if ($('.about__text')) $('.about__text').textContent = '';
  $$('.settings').forEach((section) => { section.hidden = true; });
  $$('[role="switch"][name]').forEach((input) => { input.disabled = true; });
  profileRoot?.setAttribute('aria-busy', 'true');
  try {
    loadedUser = await resolveCurrentUser();
    if (!loadedUser) {
      throw new Error('Сессия не найдена. Войдите, чтобы открыть профиль.');
    }
    if (pageName() === 'moderator-profile.html' && loadedUser.role !== 'moderator') {
      profileRoot?.replaceChildren(emptyState('Эта страница доступна только модератору.', 'Перейти в профиль', 'profile.html'));
      return;
    }
    applyProfile(loadedUser);
    const edit = $('.hero__edit, .profile-edit');
    edit?.addEventListener('click', () => showProfileDialog(loadedUser));
    $$('[role="switch"][name]').forEach((input) => input.addEventListener('change', async () => {
      const preferences = { ...(loadedUser.notification_preferences || {}) };
      preferences[input.name] = input.checked;
      try {
        loadedUser = await updateProfile({ notification_preferences: preferences });
      } catch (error) {
        input.checked = !input.checked;
        notify(error.message, 'error');
      }
    }));
    if (pageName() === 'profile.html') await loadOwnListings();
  } catch (error) {
    profileRoot?.replaceChildren(emptyState('Войдите, чтобы открыть личный кабинет.', 'Войти', 'login.html'));
    notify(`Не удалось загрузить профиль: ${error.message}`, 'error');
  }
}

async function loadMessages() {
  const app = $('#messages-app');
  if (!app) return;
  const list = $('#conversation-list', app);
  const feed = $('#message-feed', app);
  const form = $('#message-form', app);
  let selectedConversation = null;
  try {
    const conversations = asItems(await getConversations());
    list.replaceChildren();
    if (!conversations.length) {
      list.append(emptyState('Диалогов пока нет. Откройте объявление и нажмите «Написать».'));
      return;
    }
    conversations.forEach((conversation) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'conversation-link';
      button.textContent = conversation.last_message?.text || 'Новый диалог';
      button.dataset.conversationId = conversation.id;
      button.dataset.participantId = conversation.participant_id || '';
      button.addEventListener('click', () => {
        selectedConversation = conversation;
        location.hash = conversation.id;
        showConversation(conversation, list, feed, form);
      });
      list.append(button);
    });
    selectedConversation = conversations.find((item) => String(item.id) === listingIdFromHash()) || conversations[0];
    if (!listingIdFromHash()) location.hash = selectedConversation.id;
    await showConversation(selectedConversation, list, feed, form);
    try {
      let socket;
      socket = connectNotifications({
        onEvent: async (event) => {
          const latest = asItems(await getConversations()).find((item) => item.id === selectedConversation?.id);
          if (latest) {
            selectedConversation = latest;
            await showConversation(latest, list, feed, form);
          }
          if (event.event_id) socket?.send(JSON.stringify({ type: 'ack', event_id: event.event_id }));
        },
      });
    } catch { /* HTTP conversation history remains available if notifications are offline. */ }
  } catch (error) {
    list?.replaceChildren(emptyState(`Не удалось загрузить сообщения: ${error.message}`, 'Войти', 'login.html'));
  }
}

async function showConversation(conversation, list, feed, form) {
  if (!conversation?.id) return;
  const participantId = conversation.participant_id || conversation.participants?.find((id) => id !== loadedUser?.user_id);
  form.dataset.participantId = participantId || '';
  $$('.conversation-link', list).forEach((link) => link.classList.toggle('is-active', link.dataset.conversationId === conversation.id));
  try {
    const history = asItems(await getConversation(conversation.id));
    feed.replaceChildren();
    history.slice().reverse().forEach((message) => {
      const bubble = document.createElement('article');
      bubble.className = `message-bubble${message.sender_id === loadedUser?.user_id ? ' message-bubble--own' : ''}`;
      const text = document.createElement('p');
      text.textContent = message.text || '';
      const time = document.createElement('time');
      time.dateTime = message.created_at || '';
      time.textContent = message.created_at ? new Date(message.created_at).toLocaleString('ru-RU') : '';
      bubble.append(text, time);
      feed.append(bubble);
    });
    feed.scrollTop = feed.scrollHeight;
    const unread = history.filter((message) => message.receiver_id === loadedUser?.user_id && !message.read_at).map((message) => message.id);
    if (unread.length) await markMessagesRead(unread).catch(() => {});
  } catch (error) {
    feed.replaceChildren(emptyState(`Не удалось загрузить историю: ${error.message}`));
  }
}

function bindMessages() {
  const form = $('#message-form');
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = $('textarea, input[name="text"]', form);
    const text = input?.value.trim();
    if (!text) return;
    try {
      const result = await sendMessage(form.dataset.participantId, text);
      input.value = '';
      notify(result?.status === 'accepted' ? 'Сообщение отправлено.' : 'Сообщение принято.');
      const conversation = asItems(await getConversations()).find((item) => item.id === listingIdFromHash());
      if (conversation) await showConversation(conversation, $('#conversation-list'), $('#message-feed'), form);
    } catch (error) {
      notify(error.message, 'error');
    }
  });
}

function pageName() {
  return location.pathname.split('/').pop() || 'index.html';
}

function bindGlobalUi() {
  $('.header__toggle')?.addEventListener('click', (event) => {
    const button = event.currentTarget;
    const nav = $('.header__nav');
    const open = nav?.classList.toggle('is-open') || false;
    button.setAttribute('aria-expanded', String(open));
  });
  $$('a[href="#"]').forEach((link) => link.addEventListener('click', (event) => event.preventDefault()));
  $$('a[href="analytics.html"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      notify('Аналитический API пока не подключён через Gateway.');
    });
  });
  $$('a.nav__link').forEach((link) => {
    if ($('.nav__text', link)?.textContent.includes('Сообщения')) link.href = 'messages.html';
  });
  document.addEventListener('change', (event) => {
    const target = event.target;
    if (target.matches('input[type="file"]')) {
      const label = target.closest('.upload')?.querySelector('.upload__text');
      if (label) label.textContent = target.files?.length > 1 ? `Выбрано файлов: ${target.files.length}` : target.files?.[0]?.name || 'Загрузить файл';
    }
    if (!target.matches('.dropdown__list input') || target.closest('.catalog-form')) return;
    const dropdown = target.closest('details.dropdown');
    if (!dropdown) return;
    const value = $('.dropdown__value', dropdown);
    if (!value) return;
    const selected = $$('input:checked', dropdown).filter((input) => input.value !== 'all');
    value.textContent = selected.map((input) => input.dataset.short || $('span:last-child', input.closest('.option'))?.textContent.trim()).filter(Boolean).join(', ') || 'Выберите из списка';
  });
  document.addEventListener('click', (event) => {
    const apply = event.target.closest('.dropdown__apply');
    if (apply) apply.closest('details.dropdown')?.removeAttribute('open');
  });
  document.addEventListener('click', (event) => {
    const favorite = event.target.closest('.card__fav, .listing__fav, .summary__fav, .business-offer__favorite');
    if (favorite) {
      const card = favorite.closest('[data-listing-id]');
      const id = favorite.dataset.listingId || card?.dataset.listingId;
      if (!id) {
        event.preventDefault();
        return notify('Это предложение не связано с опубликованным объявлением.', 'error');
      }
      const active = !favoriteIds().includes(String(id));
      saveFavorite(id, active);
      updateIconFavorite(favorite, active);
    }
  });
  const logoutLink = $('[data-logout]');
  logoutLink?.addEventListener('click', async (event) => {
    event.preventDefault();
    logoutLink.disabled = true;
    try {
      await logout();
      location.href = 'index.html';
    } catch (error) {
      logoutLink.disabled = false;
      notify(`Не удалось завершить сеанс: ${error.message}`, 'error');
    }
  });
}

async function bindBlacklist() {
  const list = $('.blacklist__list');
  if (!list) return;
  const search = $('.bl-search__input');
  const found = $('.bl-found');
  const banForm = $('.bl-add');
  let entries = [];
  const render = () => {
    const query = search?.value.trim().toLowerCase() || '';
    const filtered = entries.filter((entry) => `${entry.user_id} ${entry.reason}`.toLowerCase().includes(query));
    list.replaceChildren();
    if (found) found.textContent = `Найдено: ${filtered.length}`;
    if (!filtered.length) {
      const empty = document.createElement('li');
      empty.append(emptyState(query ? 'Совпадений не найдено.' : 'Чёрный список пуст.'));
      list.append(empty);
      return;
    }
    filtered.forEach((entry) => {
      const item = document.createElement('li');
      const card = document.createElement('article');
      card.className = 'user-card';
      const avatar = document.createElement('div');
      avatar.className = 'user-card__avatar';
      avatar.setAttribute('aria-hidden', 'true');
      const info = document.createElement('div');
      info.className = 'user-card__info';
      const name = document.createElement('h2');
      name.className = 'user-card__name';
      name.textContent = 'Пользователь';
      const reason = document.createElement('p');
      reason.className = 'user-card__contacts';
      reason.textContent = `Причина: ${entry.reason}`;
      info.append(name, reason);
      const idBlock = document.createElement('dl');
      idBlock.className = 'user-card__id';
      const term = document.createElement('dt');
      term.textContent = 'ID пользователя';
      const value = document.createElement('dd');
      value.textContent = entry.user_id;
      idBlock.append(term, value);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'user-card__btn user-card__btn--outline';
      button.textContent = 'Разблокировать';
      button.addEventListener('click', async () => {
        try {
          await removeFromBlacklist(entry.user_id);
          entries = entries.filter((row) => row.user_id !== entry.user_id);
          render();
          notify('Пользователь разблокирован. Объявления остаются снятыми с каталога.');
        } catch (error) { notify(error.message, 'error'); }
      });
      card.append(avatar, info, idBlock, button);
      item.append(card);
      list.append(item);
    });
  };
  $('.bl-search')?.addEventListener('submit', (event) => event.preventDefault());
  search?.addEventListener('input', render);
  banForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(banForm);
    const userId = String(data.get('user_id') || '').trim();
    const reason = String(data.get('reason') || '').trim();
    try {
      await addToBlacklist(userId, reason);
      banForm.reset();
      entries = await getBlacklist();
      render();
      notify('Пользователь заблокирован, его объявления будут сняты с каталога.');
    } catch (error) { notify(error.message, 'error'); }
  });
  try {
    entries = await getBlacklist();
    render();
  } catch (error) {
    list.replaceChildren();
    const item = document.createElement('li');
    item.append(emptyState(`Не удалось загрузить чёрный список: ${error.message}`));
    list.append(item);
  }
}

async function bindHome() {
  const homeUser = await resolveHomeUser();
  applyHomeAccountState(homeUser);
  const grid = $('.offers .business-grid');
  if (!grid) return;
  try {
    const template = $('.business-offer', grid);
    grid.replaceChildren(emptyState('Загрузка предложений…'));
    const rows = asItems(await search({ limit: 3, sort: 'newest' })).slice(0, 3);
    if (!rows.length) {
      const empty = emptyState('Новые предложения появятся здесь после публикации объявлений.', 'Открыть каталог', homeUser ? 'catalog.html' : 'login.html');
      const emptyLink = $('a', empty);
      if (emptyLink) {
        emptyLink.dataset.authDestination = 'catalog.html';
        emptyLink.dataset.homeAuthenticated = String(Boolean(homeUser));
      }
      grid.replaceChildren(empty);
      return;
    }
    grid.replaceChildren();
    rows.forEach((item) => {
      const card = template.cloneNode(true);
      card.dataset.listingId = item.listing_id;
      $('.business-offer__title', card).textContent = item.business_name || 'Бизнес на продаже';
      $('.business-offer__meta', card).textContent = [item.location?.city, displayEnum(item.business_type)].filter(Boolean).join(' · ');
      const finances = item.monthly_financials || [];
      const averageProfit = finances.length
        ? finances.reduce((sum, row) => sum + Number(row.net_profit || 0), 0) / finances.length
        : undefined;
      const paybackMonths = Number(item.sale_price) > 0 && Number(averageProfit) > 0
        ? Number(item.sale_price) / Number(averageProfit)
        : undefined;
      const values = $$('.business-offer__stat .business-offer__value', card);
      if (values[0]) values[0].textContent = formatMoney(item.sale_price);
      if (values[1]) values[1].textContent = averageProfit === undefined ? 'Нет данных' : `${formatMoney(averageProfit)} / мес.`;
      if (values[2]) values[2].textContent = paybackMonths === undefined ? 'Нет данных' : `${paybackMonths.toLocaleString('ru-RU', { maximumFractionDigits: 1 })} мес.`;
      $('.business-offer__rating', card)?.remove();
      if (averageProfit === undefined && values[1]) values[1].closest('.business-offer__stat').hidden = true;
      if (paybackMonths === undefined && values[2]) values[2].closest('.business-offer__stat').hidden = true;
      placeImage($('.business-offer__photo', card), item.main_photo || item.photos?.[0]);
      const more = $('.business-offer__details', card);
      if (more) {
        const destination = `listing.html#${encodeURIComponent(item.listing_id)}`;
        more.dataset.authDestination = destination;
        more.dataset.homeAuthenticated = String(Boolean(homeUser));
        more.href = homeUser ? destination : 'login.html';
      }
      const favorite = $('.business-offer__favorite', card);
      if (favorite) {
        favorite.dataset.listingId = item.listing_id;
        updateIconFavorite(favorite, favoriteIds().includes(String(item.listing_id)));
      }
      grid.append(card);
    });
  } catch (error) {
    notify(`Не удалось загрузить предложения: ${error.message}`, 'error');
  }
}

async function resolveHomeUser() {
  try {
    return await resolveCurrentUser();
  } catch { return null; }
}

async function resolveCurrentUser() {
  if (!getAccessToken() && !(await restoreSession())) return null;
  try {
    return await me();
  } catch (error) {
    if (error.status !== 401) throw error;
    setAccessToken(null);
    if (!(await restoreSession())) return null;
    return me();
  }
}

function applyHomeAccountState(user) {
  const authenticated = Boolean(user);
  $$('[data-home-guest]').forEach((element) => { element.hidden = authenticated; });
  const avatarLink = $('[data-home-avatar]');
  if (avatarLink) {
    avatarLink.hidden = !authenticated;
    if (authenticated) {
      const nameParts = [user.first_name, user.last_name].filter((part) => typeof part === 'string' && part.trim());
      const fallbackName = user.email || 'Профиль';
      const initials = nameParts.length
        ? `${nameParts[0][0]}${nameParts.length > 1 ? nameParts[nameParts.length - 1][0] : ''}`
        : fallbackName.slice(0, 2);
      const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || fallbackName;
      const initialsElement = $('[data-home-avatar-initials]', avatarLink);
      const image = $('[data-home-avatar-image]', avatarLink);
      if (initialsElement) initialsElement.textContent = initials.toLocaleUpperCase('ru-RU');
      avatarLink.setAttribute('aria-label', `Открыть профиль: ${name}`);
      avatarLink.href = user.role === 'moderator' ? 'moderator-profile.html' : 'profile.html';
      if (image) {
        let avatarUrl = null;
        try { if (user.avatar) avatarUrl = new URL(user.avatar, location.href); } catch { /* Use initials for an invalid avatar URL. */ }
        const useAvatar = avatarUrl && avatarUrl.origin === location.origin && ['http:', 'https:'].includes(avatarUrl.protocol);
        image.hidden = !useAvatar;
        if (initialsElement) initialsElement.hidden = Boolean(useAvatar);
        image.onerror = () => {
          image.hidden = true;
          if (initialsElement) initialsElement.hidden = false;
        };
        if (useAvatar) image.src = avatarUrl.href;
        else image.removeAttribute('src');
      }
    }
  }
  $$('[data-auth-destination]').forEach((link) => {
    link.dataset.homeAuthenticated = String(authenticated);
    link.href = authenticated ? link.dataset.authDestination : 'login.html';
  });
  if (!document.documentElement.dataset.homeAuthClickBound) {
    document.documentElement.dataset.homeAuthClickBound = 'true';
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[data-auth-destination]');
      if (!link || link.dataset.homeAuthenticated === 'true') return;
      event.preventDefault();
      sessionStorage.setItem('mieroventure.redirect', safeInternalDestination(link.dataset.authDestination));
      location.href = 'login.html';
    });
  }
}

function initNotificationsAndAuth() {
  const protectedPages = new Set(['profile.html', 'my-listings.html', 'create-listing.html', 'moderation-queue.html', 'moderation-detail.html', 'blacklist.html', 'moderator-profile.html', 'messages.html']);
  if (protectedPages.has(pageName()) && !getAccessToken()) {
    restoreSession().catch(() => false);
  }
}

function start() {
  bindGlobalUi();
  registerAuthForms();
  bindCatalog();
  bindCreateListing();
  bindMessages();
  initNotificationsAndAuth();

  const page = pageName();
  if (page === 'index.html') bindHome();
  if (page === 'favorites.html') loadFavorites();
  if (page === 'my-listings.html') loadOwnListings();
  if (page === 'profile.html' || page === 'moderator-profile.html') loadProfile();
  if (page === 'listing.html') loadListingDetail();
  if (page === 'moderation-queue.html') loadModerationQueue();
  if (page === 'moderation-detail.html') bindModerationDetail();
  if (page === 'blacklist.html') bindBlacklist();
  if (page === 'messages.html') {
    resolveCurrentUser().then((user) => {
      if (!user) throw new Error('Войдите, чтобы открыть сообщения.');
      loadedUser = user;
      return loadMessages();
    })
      .catch((error) => notify(`Войдите, чтобы открыть сообщения: ${error.message}`, 'error'));
  }
}

start();
