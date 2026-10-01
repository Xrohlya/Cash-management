import { money, showToast } from "./core.js?v=20261001-3";
import { element, iconButton } from "./ui.js?v=20261001-3";

export function renderLimits(planning, state) {
  const root = document.getElementById("category-limits-list");
  const notice = document.getElementById("budget-limit-notice");
  const reached = planning.limits.filter((item) => item.status !== "green");
  notice.hidden = reached.length === 0;
  notice.textContent = `Внимание к лимитам: ${reached.map((item) => item.category).join(", ")}`;
  notice.dataset.status = reached.some((item) => item.status === "red") ? "red" : "yellow";
  document.getElementById("expense-categories").replaceChildren(...planning.categories.map((name) => new Option(name, name)));
  if (!planning.limits.length) {
    root.replaceChildren(element("p", "compact-empty financial-note", "Лимиты пока не заданы"));
    return;
  }
  root.replaceChildren(...planning.limits.map((item) => {
    const row = element("article", "limit-item");
    row.dataset.status = item.status;
    const label = element("div");
    label.append(element("strong", "", item.category), element("small", "", `${money(item.spent)} из ${money(item.amount)} · ${item.progress}%`));
    const status = item.status === "red" ? "Лимит достигнут" : item.status === "yellow" ? "Использовано 80% или больше" : `Осталось ${money(item.remaining)}`;
    label.append(element("small", "", status));
    const actions = element("div", "limit-actions");
    const edit = iconButton("pencil", "Изменить лимит");
    edit.dataset.limitEdit = item.category;
    const remove = iconButton("x", "Удалить лимит", "mini-icon danger");
    remove.dataset.limitDelete = item.category;
    actions.append(edit, remove);
    const track = element("span", "limit-track");
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-label", item.category);
    track.setAttribute("aria-valuenow", Math.min(100, item.progress));
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    const fill = element("i");
    fill.style.width = `${Math.min(100, Math.max(0, item.progress))}%`;
    track.append(fill);
    row.append(label, actions, track);
    return row;
  }));
  const warnings = [];
  for (const item of planning.limits) {
    if (item.status === "green") continue;
    const key = `limit:${state.profile.id}:${state.period_start}:${item.category}:${item.amount}:${item.status}`;
    try {
      if (sessionStorage.getItem(key)) continue;
      sessionStorage.setItem(key, "seen");
      warnings.push(item.category);
    } catch { /* Visible limit indicators remain available without browser storage. */ }
  }
  if (warnings.length) showToast(`Проверьте лимиты: ${warnings.join(", ")}`);
}
