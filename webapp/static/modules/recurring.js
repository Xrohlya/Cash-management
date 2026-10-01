import { money } from "./core.js?v=20261001-1";

function renderRecurring(items) {
  const root = document.getElementById("recurring-list");
  if (!items.length) {
    root.innerHTML = '<p class="empty">Регулярных платежей пока нет</p>';
    return;
  }
  root.replaceChildren(...items.map((item) => {
    const row = document.createElement("article");
    row.className = "recurring-item";
    row.innerHTML = `<div><strong></strong><small></small></div><b></b>`;
    row.querySelector("strong").textContent = item.title;
    row.querySelector("small").textContent = `${item.day_of_month}-го числа · ${item.kind === "rent" ? "Квартира" : "Расход"}`;
    row.querySelector("b").textContent = money(item.amount);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "delete-button";
    remove.dataset.recurringDelete = item.id;
    remove.setAttribute("aria-label", `Удалить ${item.title}`);
    remove.title = "Удалить";
    remove.textContent = "×";
    row.append(remove);
    return row;
  }));
}

function renderUpcomingPayment(items) {
  const root = document.getElementById("upcoming-payment");
  const active = items.filter((item) => Number(item.active));
  if (!active.length) {
    root.hidden = true;
    return;
  }
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const upcoming = active.map((item) => {
    let due = new Date(now.getFullYear(), now.getMonth(), Number(item.day_of_month));
    if (due < today) due = new Date(now.getFullYear(), now.getMonth() + 1, Number(item.day_of_month));
    return { item, due };
  }).sort((a, b) => a.due - b.due)[0];
  document.getElementById("upcoming-title").textContent = upcoming.item.title;
  document.getElementById("upcoming-amount").textContent = money(upcoming.item.amount);
  document.getElementById("upcoming-date").textContent = new Intl.DateTimeFormat("ru-RU", {
    day: "numeric", month: "long",
  }).format(upcoming.due);
  root.hidden = false;
}

export { renderRecurring, renderUpcomingPayment };
