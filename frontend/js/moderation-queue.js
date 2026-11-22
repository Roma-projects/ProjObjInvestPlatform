const sort = document.querySelector(".queue-sort");
const list = document.querySelector(".queue-list");
const sortLabel = document.querySelector(".queue-sort__value");
const notify = document.querySelector(".notify");
const notifyButton = document.querySelector(".notify__button");
const notifyPanel = document.querySelector(".notify__panel");

const compare = {
  date: (a, b) => Number(a.dataset.order) - Number(b.dataset.order),
  price: (a, b) => Number(b.dataset.price) - Number(a.dataset.price),
  score: (a, b) => Number(b.dataset.score) - Number(a.dataset.score),
  risk: (a, b) => Number(b.dataset.risk) - Number(a.dataset.risk)
};

if (sort && list) {
  sort.addEventListener("change", (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.name !== "queue-sort") return;

    const cards = [...list.querySelectorAll(".queue-card")];
    const byKey = compare[input.value] || compare.date;
    cards.sort((a, b) => {
      const diff = byKey(a, b);
      return diff || Number(a.dataset.order) - Number(b.dataset.order);
    });
    cards.forEach((card) => list.appendChild(card));

    if (sortLabel && input.dataset.label) sortLabel.textContent = input.dataset.label;
    sort.open = false;
  });
}

if (notify && notifyButton && notifyPanel) {
  notifyButton.addEventListener("click", () => {
    const open = notifyPanel.hasAttribute("hidden");
    notifyPanel.toggleAttribute("hidden", !open);
    notifyButton.setAttribute("aria-expanded", String(open));
  });
}

document.addEventListener("click", (event) => {
  if (sort && !sort.contains(event.target)) sort.open = false;
  if (notify && notifyPanel && !notify.contains(event.target)) {
    notifyPanel.hidden = true;
    notifyButton.setAttribute("aria-expanded", "false");
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (sort) sort.open = false;
  if (notifyPanel && notifyButton) {
    notifyPanel.hidden = true;
    notifyButton.setAttribute("aria-expanded", "false");
  }
});
