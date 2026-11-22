/* ==========================================================================
   create-listing.js — страница «Создание объявления»
   Подключается отдельно от main.js:
   <script src="../js/create-listing.js" defer></script>
   ========================================================================== */
(() => {
  const wizard = document.querySelector(".wizard__form");
  if (!wizard) return;

  let cloneId = 100;

  /* ---------- Подпись в строке выпадающего списка ---------- */
  const updateLabel = (dropdown) => {
    const valueEl = dropdown.querySelector(".dropdown__value");
    if (!valueEl) return;
    valueEl.dataset.placeholder ??= valueEl.textContent.trim();

    const checked = dropdown.querySelector(".option__input:checked");
    valueEl.textContent =
      checked && checked.value !== "all"
        ? checked.closest(".option").lastElementChild.textContent.trim()
        : valueEl.dataset.placeholder;
  };

  /* ---------- Добавление блока: оборудование / сотрудник / месяц ---------- */
  const addItem = (group) => {
    const items = wizard.querySelectorAll(`[data-repeat="${group}"]`);
    const last = items[items.length - 1];
    if (!last) return;

    const clone = last.cloneNode(true);

    /* очистить поля */
    clone
      .querySelectorAll("input:not([type='radio']):not([type='checkbox']), textarea")
      .forEach((el) => (el.value = ""));
    clone.querySelectorAll("select").forEach((el) => (el.selectedIndex = 0));
    clone.querySelectorAll("details").forEach((d) => (d.open = false));

    /* у радиокнопок копии должно быть своё имя, иначе они «склеятся» с оригиналом */
    clone.querySelectorAll("input[type='radio']").forEach((radio) => {
      radio.name = radio.name.replace(/_\d+$/, "") + "_" + ++cloneId;
      radio.checked = false;
    });

    /* вернуть подписи «Выберите из списка» */
    clone.querySelectorAll(".dropdown__value").forEach((el) => {
      if (el.dataset.placeholder) el.textContent = el.dataset.placeholder;
    });

    last.after(clone);
    clone.querySelector("input:not([type='radio']), textarea")?.focus();
  };

  /* ---------- Клики ---------- */
  wizard.addEventListener("click", (e) => {
    /* «+ Добавить …» */
    const addBtn = e.target.closest("[data-add]");
    if (addBtn) {
      addItem(addBtn.dataset.add);
      return;
    }

    /* «Применить» закрывает список */
    const apply = e.target.closest(".dropdown__apply");
    if (apply) apply.closest("details").open = false;
  });

  /* ---------- Выбор пункта / файла ---------- */
  wizard.addEventListener("change", (e) => {
    const dropdown = e.target.closest(".dropdown");
    if (dropdown) updateLabel(dropdown);

    if (e.target.matches(".upload__input")) {
      const text = e.target.closest(".upload").querySelector(".upload__text");
      const files = e.target.files;
      text.textContent =
        files.length > 1 ? `Файлов: ${files.length}` : files[0]?.name || "Загрузить файл";
    }
  });

  /* ---------- Маска времени ЧЧ:ММ (поля с классом js-time) ---------- */
  wizard.addEventListener("input", (e) => {
    if (!e.target.matches(".js-time")) return;

    let digits = e.target.value.replace(/\D/g, "").slice(0, 4);

    /* первая цифра часов больше 2 → ставим ноль: 9 → 09 */
    if (digits.length === 1 && Number(digits) > 2) digits = "0" + digits;
    /* часы не больше 23 */
    if (digits.length >= 2 && Number(digits.slice(0, 2)) > 23) digits = "23" + digits.slice(2);
    /* минуты не больше 59: первая цифра минут 6-9 → 5 */
    if (digits.length >= 3 && Number(digits[2]) > 5) digits = digits.slice(0, 2) + "5" + digits.slice(3);

    e.target.value = digits.length > 2 ? digits.slice(0, 2) + ":" + digits.slice(2) : digits;
  });

  /* ---------- Закрытие списков: клик вне и Esc ---------- */
  document.addEventListener("click", (e) => {
    wizard.querySelectorAll(".dropdown[open]").forEach((d) => {
      if (!d.contains(e.target)) d.open = false;
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      wizard.querySelectorAll(".dropdown[open]").forEach((d) => (d.open = false));
    }
  });
})();
