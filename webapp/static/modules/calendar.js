import { money } from "./core.js?v=20261001-2";
import { element } from "./ui.js?v=20261001-2";

export function renderCalendar(events) {
  const calendar = document.getElementById("money-calendar-list");
  const labels = { income: "Получено", planned_income: "Ожидается · не в балансе", payment: "Запланированный платёж", period: "Граница периода" };
  if (!events.length) {
    calendar.replaceChildren(element("p", "compact-empty financial-note", "Событий пока нет"));
    return;
  }
  calendar.replaceChildren(...events.map((event) => {
    const row = element("article", `calendar-event calendar-${event.kind}`);
    const dateValue = new Date(`${event.date}T12:00:00`);
    const dateBlock = element("time");
    dateBlock.dateTime = event.date;
    dateBlock.append(element("b", "", String(dateValue.getDate())), element("span", "", new Intl.DateTimeFormat("ru-RU", { month: "short" }).format(dateValue)));
    const info = element("div");
    info.append(element("strong", "", event.title), element("small", "", labels[event.kind] || event.kind));
    row.append(dateBlock, info);
    if (event.amount > 0) row.append(element("b", "", `${["income", "planned_income"].includes(event.kind) ? "+" : "−"}${money(event.amount)}`));
    return row;
  }));
}
