import { money } from "./core.js?v=20261001-2";
import { element, dateLabel } from "./ui.js?v=20261001-2";

export function renderWeekly(weekly) {
  document.getElementById("week-period").textContent = `${dateLabel(weekly.start)} — ${dateLabel(weekly.end)}`;
  const metrics = [["Обычные расходы", weekly.spent], ["Доход после удержаний", weekly.net_income], ["Отложено", weekly.saved], ["Квартира и регулярные", weekly.payments]];
  document.getElementById("week-metrics").replaceChildren(...metrics.map(([label, amount]) => {
    const node = element("div");
    node.append(element("span", "", label), element("b", "", money(amount)));
    return node;
  }));
  document.getElementById("week-insights").replaceChildren(...weekly.insights.map((text) => element("li", "", text)));
}
