import { money } from "./core.js?v=20261001-3";
import { element, iconButton, dateLabel } from "./ui.js?v=20261001-3";

export function renderPlans(planning, sources) {
  document.getElementById("forecast-planned").textContent = money(planning.projected_with_income);
  document.getElementById("expected-total").textContent = `Ожидается ${money(planning.expected_total)}`;
  const select = document.getElementById("planned-income-source");
  const selected = select.value;
  const options = [new Option("Без удержания", "")];
  sources.filter((source) => Number(source.active)).forEach((source) => {
    options.push(new Option(`${source.name} · ${source.withholding_percent}%`, String(source.id)));
  });
  select.replaceChildren(...options);
  select.value = options.some((option) => option.value === selected) ? selected : "";
  const root = document.getElementById("planned-income-list");
  if (!planning.plans.length) {
    root.replaceChildren(element("p", "compact-empty financial-note", "Поступления пока не запланированы"));
    return;
  }
  const today = new Date().toLocaleDateString("sv-SE");
  root.replaceChildren(...planning.plans.map((plan) => {
    const row = element("article", "plan-item");
    const heading = element("div");
    heading.append(element("strong", "", plan.title), element("b", "", money(plan.net)));
    const overdue = plan.due_date < today;
    const detail = `${dateLabel(plan.due_date)}${overdue ? " · дата прошла" : ""} · ${plan.source_name || "Без удержания"}`;
    const info = element("small", overdue ? "overdue" : "", detail);
    const gross = element("small", "", `До удержания ${money(plan.amount)} · ${plan.withholding_percent}%`);
    const actions = element("div", "plan-actions");
    const confirm = element("button", "secondary", "Доход получен");
    confirm.type = "button";
    confirm.dataset.planConfirm = plan.id;
    confirm.disabled = !plan.source_available;
    const edit = iconButton("pencil", "Изменить поступление");
    edit.dataset.planEdit = plan.id;
    const cancel = iconButton("x", "Убрать из плана", "mini-icon danger");
    cancel.dataset.planCancel = plan.id;
    actions.append(confirm, edit, cancel);
    row.append(heading, info, gross);
    if (!plan.source_available) row.append(element("small", "overdue", "Источник удалён — выберите другой"));
    row.append(actions);
    return row;
  }));
}
