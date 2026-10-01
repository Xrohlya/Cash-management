import { money } from "./core.js?v=20261001-1";

function renderRadar(radar) {
  document.getElementById("safe-today").textContent = money(radar.safe_today);
  document.getElementById("reserved-total").textContent = money(radar.reserved);
  document.getElementById("projected-balance").textContent = `Прогноз: ${money(radar.projected_balance)}`;
  document.getElementById("target-balance-radar").textContent = money(radar.target_balance);
  document.getElementById("streak-current").textContent = `${radar.streak.current} дн.`;
  document.getElementById("streak-best").textContent = `Рекорд: ${radar.streak.best} дн.`;
  document.getElementById("weekly-total").textContent = money(radar.weekly.current);

  const change = Number(radar.weekly.change_percent || 0);
  const weeklyChange = document.getElementById("weekly-change");
  if (radar.weekly.previous === 0 && radar.weekly.current === 0) {
    weeklyChange.textContent = "Расходов не было";
  } else if (change === 0) {
    weeklyChange.textContent = "Как неделю назад";
  } else {
    weeklyChange.textContent = `${change > 0 ? "+" : ""}${change.toLocaleString("ru-RU")}% к прошлой неделе`;
  }
  weeklyChange.className = change > 0 ? "trend-worse" : change < 0 ? "trend-better" : "";

  const pill = document.getElementById("risk-pill");
  pill.className = `risk-pill risk-${radar.risk}`;
  pill.textContent = radar.risk_title;
  document.getElementById("risk-text").textContent = radar.risk_text;

  const calendar = document.getElementById("money-calendar-list");
  if (!radar.calendar.length) {
    calendar.innerHTML = '<p class="empty compact-empty">Событий пока нет</p>';
    return;
  }
  calendar.replaceChildren(...radar.calendar.map((event) => {
    const row = document.createElement("article");
    row.className = `calendar-event calendar-${event.kind}`;
    const [year, month, day] = event.date.split("-").map(Number);
    const dateValue = new Date(year, month - 1, day);
    const dateBlock = document.createElement("time");
    dateBlock.dateTime = event.date;
    dateBlock.innerHTML = `<b>${day}</b><span>${new Intl.DateTimeFormat("ru-RU", { month: "short" }).format(dateValue)}</span>`;
    const info = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = event.title;
    const kind = document.createElement("small");
    kind.textContent = event.kind === "income" ? "Поступление" : event.kind === "payment" ? "Запланированный платёж" : "Граница периода";
    info.append(title, kind);
    row.append(dateBlock, info);
    if (Number(event.amount) > 0) {
      const amount = document.createElement("b");
      amount.textContent = `${event.kind === "income" ? "+" : "−"}${money(event.amount)}`;
      row.append(amount);
    }
    return row;
  }));
}

export { renderRadar };
