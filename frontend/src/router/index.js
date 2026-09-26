/* Для чего нужен этот файл:
 * Связывает адреса страниц с компонентами интерфейса и настраивает навигацию.
 */

/**
 * Router stub — настроить React Router / Vue Router.
 * Маршруты: /, /listings/:id, /auth, /dashboard, /chat
 */
export const routes = [
  { path: '/', name: 'Home' },
  { path: '/listings/:id', name: 'Listing' },
  { path: '/auth', name: 'Auth' },
  { path: '/dashboard', name: 'Dashboard' },
  { path: '/chat', name: 'Chat' },
];

export default routes;
