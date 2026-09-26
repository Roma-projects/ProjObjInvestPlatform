/* Для чего нужен этот файл:
 * Создаёт общее хранилище состояния — данные, которыми пользуются разные части интерфейса.
 */

/**
 * Store root stub (Redux Toolkit / Zustand / Pinia — выбор за командой).
 * slices/ — модули auth, listings, chat, ui
 */
export const storePlaceholder = {
  auth: { user: null, accessToken: null },
  listings: { items: [], selectedId: null },
};

export default storePlaceholder;
