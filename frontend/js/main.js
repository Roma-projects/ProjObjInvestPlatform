const header = document.querySelector(".site-header");
const toggle = document.querySelector(".header__toggle");
const nav = document.querySelector(".header__nav");

window.addEventListener("scroll", () => {
  header?.classList.toggle("is-scrolled", window.scrollY > 24);
});

toggle?.addEventListener("click", () => {
  nav.classList.toggle("is-open");
  toggle.setAttribute("aria-expanded", nav.classList.contains("is-open"));
});

document.querySelectorAll(".header__link").forEach(link => {
  link.addEventListener("click", () => nav?.classList.remove("is-open"));
});

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll(".reveal, .stagger").forEach(el => observer.observe(el));

document.querySelectorAll(".business-offer__favorite, .card__fav").forEach(button => {
  button.addEventListener("click", () => {
    const active = button.classList.toggle("is-active");
    button.setAttribute("aria-pressed", active);
    button.setAttribute(
      "aria-label",
      active ? "Убрать из избранного" : "Добавить в избранное"
    );

    const img = button.querySelector("img");
    if (img) {
      img.src = active
        ? "/assets/icons/heart-filled.svg"
        : "/assets/icons/heart.svg";
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const timer = document.querySelector(".email-confirmation__timer");
  const resendButton = document.querySelector(
    ".email-confirmation__resend-button"
  );

  if (!timer || !resendButton) return;

  let seconds = 58;
  let interval = null;

  const updateTimer = () => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    timer.textContent = `${String(minutes).padStart(2, "0")}:${String(
      remainingSeconds
    ).padStart(2, "0")}`;

    if (seconds <= 0) {
      clearInterval(interval);

      resendButton.disabled = false;
      resendButton.classList.remove("is-disabled");
      timer.textContent = "";

      return;
    }

    seconds--;
  };

  resendButton.disabled = true;
  resendButton.classList.add("is-disabled");

  updateTimer();
  interval = setInterval(updateTimer, 1000);
});



/* ===== Каталог: фильтры и сортировка ===== */
const catalogForm = document.querySelector(".catalog-form");

if (catalogForm) {
  const dropdowns = catalogForm.querySelectorAll(".dropdown");

  /* Обновление текста выбранных фильтров; значения передаются JSON-ом на backend. */
  const updateDropdown = (dropdown) => {
    const valueEl = dropdown.querySelector(".dropdown__value");
    valueEl.dataset.placeholder ??= valueEl.textContent.trim();

    const checked = [...dropdown.querySelectorAll(".option__input:checked")]
      .filter(input => input.value !== "all");

    let text = valueEl.dataset.placeholder;

    if (checked.length) {
      const labels = checked.map(input =>
        input.closest(".option").lastElementChild.textContent.trim()
      );
      text = labels.length > 2 ? `Выбрано: ${labels.length}` : labels.join(", ");
    } else {
      const parts = [...dropdown.querySelectorAll(".field__input")]
        .filter(input => input.value.trim())
        .map(input => {
          const v = input.value.trim();
          if (input.name === "price_from") return `от ${v}`;
          if (input.name === "price_to") return `до ${v}`;
          return v;
        });
      if (parts.length) text = parts.join(" ");
    }

    valueEl.textContent = text;
  };

  dropdowns.forEach(dropdown => {
    updateDropdown(dropdown);

    /* Пункт «Все»: взаимоисключается с остальными вариантами. */
    dropdown.addEventListener("change", (e) => {
      const input = e.target;
      if (input.type === "checkbox") {
        const boxes = [...dropdown.querySelectorAll('input[type="checkbox"]')];
        const all = boxes.find(b => b.value === "all");
        const others = boxes.filter(b => b !== all);

        if (input === all && all.checked) others.forEach(b => (b.checked = false));
        else if (input !== all && input.checked && all) all.checked = false;

        if (all && !others.some(b => b.checked)) all.checked = true;
      }
      updateDropdown(dropdown);
    });

    dropdown.addEventListener("input", () => updateDropdown(dropdown));
  });

  /* Сброс фильтров: вернуть «Все варианты». */
  catalogForm.addEventListener("reset", () => {
    setTimeout(() => dropdowns.forEach(updateDropdown), 0);
  });

  /* Закрывать список по клику вне него и по Esc. */
  document.addEventListener("click", (e) => {
    dropdowns.forEach(d => {
      if (d.open && !d.contains(e.target)) d.open = false;
    });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") dropdowns.forEach(d => (d.open = false));
  });
}
